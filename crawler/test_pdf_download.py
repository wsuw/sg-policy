import asyncio
from playwright.async_api import async_playwright

async def test_pdf():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        # 测试两种 URL 格式
        urls = [
            "https://www.95598.cn/omg-static/99304271451438878686301117855414.pdf",
            "https://www.95598.cn/omg-static//omg-static/99304271451438878686301117855414.pdf",
        ]
        
        for url in urls:
            print(f"Trying url: {url}")
            try:
                resp = await context.request.get(url, timeout=20000)
                print(f"Status: {resp.status}, Content-Type: {resp.headers.get('content-type')}")
                if resp.status == 200:
                    body = await resp.body()
                    print(f"Success! Downloaded {len(body)} bytes (PDF length)")
                    with open("crawler/data/documents/test_sample.pdf", "wb") as f:
                        f.write(body)
                    print("Saved to crawler/data/documents/test_sample.pdf")
                    break
            except Exception as e:
                print(f"Failed {url}: {e}")

        await browser.close()

asyncio.run(test_pdf())
