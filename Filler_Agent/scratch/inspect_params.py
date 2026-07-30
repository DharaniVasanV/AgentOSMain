import asyncio
from playwright.async_api import async_playwright
import json

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://docs.google.com/forms/d/e/1FAIpQLSfI88YkuUtB7ATZfWxpoCnV2fspIbh1fXYeIpI9UD2GP7TgaA/viewform"
        await page.goto(url)
        await page.wait_for_selector('div[data-params]')
        blocks = await page.query_selector_all('div[data-params]')
        print(f"Found {len(blocks)} blocks with data-params")
        for i, block in enumerate(blocks):
            params_str = await block.get_attribute("data-params")
            print(f"Block {i}:")
            print("Raw params prefix:", params_str[:100])
            try:
                # Clean prefix if needed
                clean_str = params_str
                if clean_str.startswith("%.@."):
                    clean_str = clean_str[5:]
                data = json.loads(clean_str)
                print("Parsed Title:", data[1])
                print("Field Type ID:", data[3])
                # Let's inspect the choice structure
                # Typically data[4][0][1] contains choices/options
                print("Options structure:", data[4])
            except Exception as e:
                print("Error parsing:", e)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
