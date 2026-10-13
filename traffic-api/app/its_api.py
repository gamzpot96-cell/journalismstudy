import logging
import os
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
# HTTPX info logs expose apiKey in query strings.
logging.getLogger("httpx").setLevel(logging.WARNING)
ITS_API_KEY = os.getenv("ITS_API_KEY")
ITS_API_URL = "https://openapi.its.go.kr:9443/trafficInfo"

async def get_traffic_information(min_x, max_x, min_y, max_y):
    if not ITS_API_KEY or not ITS_API_KEY.strip():
        raise ValueError("ITS_API_KEY is missing")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ITS_API_URL, params={
            "apiKey": ITS_API_KEY.strip(), "type": "all", "drcType": "all",
            "minX": min_x, "maxX": max_x, "minY": min_y, "maxY": max_y,
            "getType": "json"})
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict):
        raise ValueError("ITS response must be an object")
    header = data.get("header", {})
    if not isinstance(header, dict) or str(header.get("resultCode", "00")) not in ("00", "0"):
        raise ValueError("ITS returned an application error")
    body = data.get("body")
    if not isinstance(body, dict) or not isinstance(body.get("items"), list):
        raise ValueError("ITS items must be an array")
    if any(not isinstance(item, dict) for item in body["items"]):
        raise ValueError("ITS items must contain objects")
    return data
