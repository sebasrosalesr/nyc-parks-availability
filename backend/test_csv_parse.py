import asyncio
import csv
from io import StringIO
from curl_cffi.requests import AsyncSession

async def main():
    url = "https://www.nycgovparks.org/permits/field-and-court/issued/B058/csv"
    async with AsyncSession(impersonate="chrome124") as client:
        resp = await client.get(url)
        reader = csv.DictReader(StringIO(resp.text))
        rows = list(reader)
        print("Columns:", reader.fieldnames)
        for row in rows[:3]:
            print(row["Start"], "->", row["End"], "[", row["Field"], "]")

asyncio.run(main())
