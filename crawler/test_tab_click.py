import asyncio
from playwright.async_api import async_playwright

async def test_tab_click():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("Navigating to https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014 ...")
        await page.goto("https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014", wait_until="networkidle", timeout=40000)
        await asyncio.sleep(5)

        # 检查 tab 元素
        tabs = await page.query_selector_all(".Advisory_Problem .grid-content")
        print(f"Found {len(tabs)} tabs")
        for i, tab in enumerate(tabs):
            text = await tab.inner_text()
            print(f"Tab {i}: {text.strip()}")
            await tab.click()
            await asyncio.sleep(3)
            
            # 检查 .fagui 内部的 li 或内容
            items = await page.query_selector_all(".fagui .sinfo ul li, .fagui li, .sinfo li")
            print(f"  After clicking tab '{text.strip()}', found {len(items)} policy items")
            for j, item in enumerate(items[:5]):
                item_text = await item.inner_text()
                print(f"    Item {j}: {item_text.replace(chr(10), ' | ')}")

        # 检查是否需要选择地区/省份
        province_text = await page.inner_text("#city_select")
        print(f"Current selected province: {province_text.strip()}")

        await browser.close()

asyncio.run(test_tab_click())
