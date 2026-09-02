import asyncio
import json
from playwright.async_api import async_playwright

async def inspect_policy_detail():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 监听所有的响应和请求
        async def on_response(response):
            url = response.url
            ct = response.headers.get("content-type", "")
            if "json" in ct or "api" in url or "osg" in url:
                print(f"\n[HTTP {response.status}] {url}")
                try:
                    if "json" in ct:
                        data = await response.json()
                        print(f"  -> JSON: {str(data)[:500]}")
                except Exception as e:
                    pass

        page.on("response", on_response)

        print("Navigating to 95598 policies page...")
        await page.goto("https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014", wait_until="networkidle")
        await asyncio.sleep(4)

        # 点击 Tab 政策文件
        tabs = await page.query_selector_all(".Advisory_Problem .grid-content")
        for tab in tabs:
            txt = await tab.inner_text()
            if "政策文件" in txt or "法律法规" in txt:
                print(f"Clicking tab: {txt}")
                await tab.click()
                await asyncio.sleep(3)
                break

        # 找到列表项
        items = await page.query_selector_all(".fagui .sinfo ul li")
        print(f"Found {len(items)} items")

        if items:
            item = items[0]
            print("First item text:", await item.inner_text())
            print("First item HTML:", await item.inner_html())

            # 截取点击前的整页截图和 DOM
            print("\n--- Clicking item to inspect detail ---")
            # 点击条目内的链接或条目本身
            a_elem = await item.query_selector("a") or item
            await a_elem.click()
            await asyncio.sleep(4)

            # 打印点击后页面的 URL 和 DOM 变化
            print("Current URL after click:", page.url)

            # 检查是否有新页面或弹窗
            pages = browser.contexts[0].pages
            print(f"Total open pages: {len(pages)}")

            # 检查当前页面的所有文本
            body_text = await page.inner_text("body")
            print("Body text preview (first 1000 chars):")
            print(body_text[:1000])

            # 保存点击后的完整 HTML
            full_html = await page.content()
            with open("crawler/data/detail_page_dump.html", "w", encoding="utf-8") as f:
                f.write(full_html)
            print("Saved detail page dump to crawler/data/detail_page_dump.html")

        await browser.close()

asyncio.run(inspect_policy_detail())
