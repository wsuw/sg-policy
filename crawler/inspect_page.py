import asyncio
import json
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def log_response(response):
            url = response.url
            ct = response.headers.get("content-type", "")
            if "json" in ct or "api" in url or "osgweb" in url:
                print(f"[API URL] {response.status} {url}")
                if "json" in ct:
                    try:
                        data = await response.json()
                        preview = str(data)[:200]
                        print(f"  [JSON DATA] {preview}")
                    except Exception as e:
                        pass

        page.on("response", log_response)

        print("Navigating...")
        await page.goto("https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014", wait_until="networkidle", timeout=40000)
        await asyncio.sleep(5)

        # 检查主内容区 HTML
        content = await page.content()
        with open("crawler/data/page_dump.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("Page HTML saved to crawler/data/page_dump.html")

        await browser.close()

asyncio.run(inspect())
