import asyncio
import sys
from services.form_parser import parse_google_form

async def test():
    # Public form URL from DB
    url = "https://docs.google.com/forms/d/e/1FAIpQLScXNQvMh4D7AoGJZeD28bADmzdmQEWaZeNA1T4SPL75gsLdrw/viewform"
    print("Testing parser with URL:", url)
    res = await parse_google_form(url)
    import pprint
    pprint.pprint(res)

if __name__ == "__main__":
    asyncio.run(test())
