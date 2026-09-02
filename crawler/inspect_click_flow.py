import asyncio
import json
from playwright.async_api import async_playwright

async def inspect_click_flow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("Navigating...")
        await page.goto("https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014", wait_until="networkidle")
        await asyncio.sleep(4)

        # 注入 window.open 拦截
        await page.evaluate("""() => {
            window.__captured_opens = [];
            let oldOpen = window.open;
            window.open = function(url, target, features) {
                window.__captured_opens.push({ url: url, target: target, features: features });
                return oldOpen ? oldOpen.call(window, url, target, features) : null;
            };
        }""")

        # 点击法律法规 Tab
        tabs = await page.query_selector_all(".Advisory_Problem .grid-content")
        print(f"Tabs count: {len(tabs)}")
        if tabs:
            await tabs[0].click()
            await asyncio.sleep(3)

        # 检查 Vue 实例和数据
        vue_data = await page.evaluate("""() => {
            let el = document.querySelector('.fagui');
            if (el && el.__vue__) {
                return {
                    faguiData: el.__vue__.$data,
                    methods: Object.keys(el.__vue__.$options.methods || {})
                };
            }
            let lis = document.querySelectorAll('.sinfo ul li');
            let items = [];
            for (let li of lis) {
                items.push(li.innerText);
            }
            return { rawItems: items };
        }""")
        print("Vue Data:", json.dumps(vue_data, ensure_ascii=False, indent=2))

        # 找到第一个 li 并点击
        li = await page.query_selector(".sinfo ul li")
        if li:
            print(f"\nClicking item: {await li.inner_text()}")
            await li.click()
            await asyncio.sleep(3)

            captured = await page.evaluate("() => window.__captured_opens")
            print("Captured window.open calls:", captured)

            # 检查是否有打开新的 Tab
            pages = context.pages
            print(f"Open pages count: {len(pages)}")
            for i, p_item in enumerate(pages):
                print(f"  Page {i} URL: {p_item.url}, Title: {await p_item.title()}")

        await browser.close()

asyncio.run(inspect_click_flow())
