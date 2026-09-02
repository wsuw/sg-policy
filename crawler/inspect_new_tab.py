import asyncio
from playwright.async_api import async_playwright

async def inspect_new_tab():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("Navigating...")
        await page.goto("https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014", wait_until="networkidle")
        await asyncio.sleep(4)

        # 点击法律法规
        tabs = await page.query_selector_all(".Advisory_Problem .grid-content")
        if tabs:
            await tabs[0].click()
            await asyncio.sleep(3)

        items = await page.query_selector_all(".fagui .sinfo ul li")
        if items:
            item = items[0]
            print(f"Clicking item: {await item.inner_text()}")

            # 监听新页面创建
            async with context.expect_page() as new_page_info:
                await item.click()
            new_page = await new_page_info.value
            await new_page.wait_for_load_state("networkidle")
            await asyncio.sleep(4)

            print(f"New Tab URL: {new_page.url}")
            print(f"New Tab Title: {await new_page.title()}")

            # 打印新页面的文本内容
            new_page_text = await new_page.inner_text("body")
            print("--- NEW TAB TEXT PREVIEW ---")
            print(new_page_text[:1500])

            # 保存新页面的 HTML
            new_html = await new_page.content()
            with open("crawler/data/new_tab_dump.html", "w", encoding="utf-8") as f:
                f.write(new_html)
            print("Saved new tab HTML to crawler/data/new_tab_dump.html")

        await browser.close()

asyncio.run(inspect_new_tab())
