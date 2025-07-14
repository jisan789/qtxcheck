import re
import json
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

api_id = 28345038
api_hash = '6c438bbc256629655ca14d4f74de0541'

# Important: must create session with local file path inside Vercel tmp
client = TelegramClient('./approver_session/session', api_id, api_hash)

app = FastAPI()

def clean_number(value):
    return re.sub(r'[^\d\.\-]', '', value).strip()

def parse_bot_reply_consistent(text):
    result = {
        "status": "null",
        "trader_id": "null",
        "country": "null",
        "balance": "null",
        "deposits_sum": "null",
        "withdrawals_count": "null"
    }

    trader_id = re.search(r"Trader # (\d+)", text) or re.search(r"Trader with ID = '(\d+)'", text)
    if trader_id:
        result["trader_id"] = trader_id.group(1)

    if "was not found" in text:
        return result

    result["status"] = "found"

    country = re.search(r"Country:\s*(.+)", text)
    if country:
        result["country"] = country.group(1).strip()

    balance = re.search(r"Balance:\s*\*\*\s*(.+?)\s*\*\*", text)
    if balance:
        result["balance"] = balance.group(1).strip()

    deposits_sum = re.search(r"Deposits Sum:\s*\*\*\s*(.+?)\s*\*\*", text)
    if deposits_sum:
        result["deposits_sum"] = clean_number(deposits_sum.group(1))

    withdrawals_count = re.search(r"Withdrawals Count:\s*\*\*\s*(.+?)\s*\*\*", text)
    if withdrawals_count:
        result["withdrawals_count"] = clean_number(withdrawals_count.group(1))

    return result

@app.get("/api/check")
async def check(id: str = Query(...)):
    await client.connect()
    bot = await client.get_entity("@QuotexPartnerBot")

    event_future = asyncio.Future()

    @client.on(events.NewMessage(chats=bot))
    async def handler(event):
        if id in event.raw_text and not event_future.done():
            event_future.set_result(event.raw_text)

    await client.send_message(bot, id)

    try:
        response_text = await asyncio.wait_for(event_future, timeout=10)
        await client.disconnect()
        return JSONResponse(parse_bot_reply_consistent(response_text))
    except asyncio.TimeoutError:
        await client.disconnect()
        return JSONResponse({"error": "Timeout waiting for response"}, status_code=504)
