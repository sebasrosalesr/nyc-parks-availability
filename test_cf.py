import asyncio
import httpx

async def test_httpx():
    print("Testing httpx...")
    headers = {"Accept": "application/json,text/javascript,*/*;q=0.01", "X-Requested-With": "XMLHttpRequest", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    async with httpx.AsyncClient(headers=headers) as client:
        resp = await client.get("https://www.nycgovparks.org/api/athletic-fields?datetime=2026-04-21T12:00:00+12:00")
        print(resp.status_code, resp.headers.get("x-amzn-waf-action"))

asyncio.run(test_httpx())
