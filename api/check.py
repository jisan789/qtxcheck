import re
import asyncio
from fastapi import FastAPI, Query, HTTPException
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from fastapi.responses import JSONResponse

api_id = 28345038
api_hash = '6c438bbc256629655ca14d4f74de0541'

string_session = '1BVtsOLUBu1crEID8o2mj9IKdivq4aifZ0-_5s6OLDWHQzlftgquIKw6Wf-zhDAiAwrYIRcCzA9XU8V5OgkWTpTfp2C5y-J13a5wpNbhGO6lCHk7rT-V3YUwVCZb855OFqFwzG5eLGW2NOYe68hlzqBA4ggfJJl69kTWz8bBQULBnsHN5d_04c-EJwvi4DpN-szfif5ZIkNN9thoMTeNpsXjVZpZheL316mXGcrbyq0ZlxPrTZ3EE9utSgfULrUobSuWhy8338mc_-ctvD5tTV8Ht2AV3kmBOOxl7rRuSqn4hXIHIoX1abJJEfGCMnLb_3geYPn_OKYJrK3sFp1walcYu-qfZjBs='  # Paste your generated session here

app = FastAPI()

def clean_number(value: str) -> str:
    return re.sub(r'[^\d\.\-]', '', value).strip()

def parse_bot_reply_consistent(text: str) -> dict:
    result = {
        "status": "null",
        "trader_id": "null",
        "country": "null",
        "balance": "null",
        "deposits_sum": "null",
        "withdrawals_count": "null"
    }

    trader_id = re.search(r"Trader # (\d+)", text)
    if not trader_id:
        trader_id = re.search(r"Trader with ID = '(\d+)'", text)
    if trader_id:
        result["trader_id"] = trader_id.group(1)

    if "Trader with ID" in text and "was not found" in text:
        return result

    result["status"] = "found"

    country = re.search(r"Country:\s*(.+)", text)
    if country:
        result["country"] = country.group(1).strip()

    balance = re.search(r"Balance:\s*([^\n\r]+)", text)
    if balance:
        result["balance"] = clean_number(balance.group(1))

    deposits_sum = re.search(r"Deposits Sum:\s*([^\n\r]+)", text)
    if deposits_sum:
        result["deposits_sum"] = clean_number(deposits_sum.group(1))

    withdrawals_count = re.search(r"Withdrawals Count:\s*([^\n\r]+)", text)
    if withdrawals_count:
        result["withdrawals_count"] = clean_number(withdrawals_count.group(1))

    return result

@app.get("/check")
async def check_trader(id: str = Query(..., min_length=5, max_length=20)):
    # Create a new client instance for every request
    client = TelegramClient(StringSession(string_session), api_id, api_hash)
    await client.start()

    bot = await client.get_entity("@QuotexPartnerBot")
    event_future = asyncio.Future()

    @client.on(events.NewMessage(chats='@QuotexPartnerBot'))
    async def response_handler(event):
        if id in event.raw_text and not event_future.done():
            event_future.set_result(event.raw_text)

    # Send the id to the bot
    await client.send_message(bot, id)

    try:
        response_text = await asyncio.wait_for(event_future, timeout=10)
        parsed = parse_bot_reply_consistent(response_text)
        await client.disconnect()
        return JSONResponse(parsed)
    except asyncio.TimeoutError:
        await client.disconnect()
        raise HTTPException(status_code=504, detail="Timeout waiting for bot response")
    except Exception as e:
        await client.disconnect()
        raise HTTPException(status_code=500, detail=str(e))
