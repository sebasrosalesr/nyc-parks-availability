import asyncio
from curl_cffi.requests import AsyncSession

async def main():
    url = "https://www.nycgovparks.org/permits/field-and-court/issued/B058/csv"
    async with AsyncSession(impersonate="chrome124") as client:
        resp = await client.get(url)
        print("Status", resp.status_code)
        print("Content-Type", resp.headers.get("Content-Type"))
        snippet = resp.text[:1000]
        print("Data Snippet:\n", snippet)

asyncio.run(main())
