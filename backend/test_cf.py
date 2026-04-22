import asyncio
from curl_cffi.requests import AsyncSession

async def test_curl_cffi():
    headers = {
        "Accept": "application/json,text/javascript,*/*;q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }
    # Using the exact payload from live_availability.py
    params = {"datetime": "2026-04-21+12:00"}
    async with AsyncSession(impersonate="chrome124") as client:
        resp = await client.get("https://www.nycgovparks.org/api/athletic-fields", params=params, headers=headers)
        print("CURL_CFFI:", resp.status_code)
        try:
            print("DATA:", str(resp.json())[:200])
        except Exception as e:
            print("Not JSON:", resp.text[:100])

asyncio.run(test_curl_cffi())
