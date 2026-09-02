import asyncio
from playwright.async_api import async_playwright

async def inspect_detail():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def log_res(r):
            if "api" in r.url or "json" in r.headers.get("content-type", ""):
                print(f"[API] {r.url}")

        page.on("response", log_res)

        print("Opening...")
        await page.goto("https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014", wait_until="networkidle")
        await asyncio.sleep(4)

        # 打印列表项
        items = await page.query_selector_all(".fagui .sinfo ul li")
        print(f"Items found: {len(items)}")
        if items:
            first_item = items[0]
            print(f"First item text: {await first_item.inner_text()}")
            
            # 点击第一条
            print("Clicking first item...")
            await first_item.click()
            await asyncio.sleep(4)

            # 打印当前页面所有可见 dialog 或主要区域
            dialogs = await page.query_selector_all(".el-dialog__wrapper, .el-dialog, .el-message-box, .modal, .content")
            print(f"Dialogs found: {len(dialogs)}")
            for d in dialogs:
                if await d.is_visible():
                    print("--- VISIBLE DIALOG ---")
                    print(await d.inner_text())

            # 检查页面是否跳转了路由
            print(f"Current Page URL after click: {page.url}")

        await browser.close()

asyncio.run(inspect_detail())
