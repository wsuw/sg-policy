import asyncio
from playwright.async_api import async_playwright

async def inspect_elements():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Navigating...")
        await page.goto("https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014", wait_until="networkidle")
        await asyncio.sleep(4)

        # 点击法律法规
        tabs = await page.query_selector_all(".Advisory_Problem .grid-content")
        if tabs:
            await tabs[0].click()
            await asyncio.sleep(3)

        items = await page.query_selector_all(".fagui .sinfo ul li")
        print(f"Items count: {len(items)}")
        for i, it in enumerate(items):
            html = await it.evaluate("el => el.outerHTML")
            print(f"\nItem {i} HTML:")
            print(html)

            # 打印绑定的 Vue 数据或者属性
            vue_data = await it.evaluate("""el => {
                if (el.__vue__) {
                    return {
                        data: el.__vue__.$data,
                        props: el.__vue__.$props,
                        vnode: el.__vue__.$vnode ? el.__vue__.$vnode.data : null
                    };
                }
                let parent = el.closest('.fagui');
                if (parent && parent.__vue__) {
                    return {
                        parentData: parent.__vue__.$data,
                    };
                }
                return null;
            }""")
            print(f"Vue component info: {vue_data}")

        # 检查整个页面的 Vue 根组件数据
        app_vue = await page.evaluate("""() => {
            let app = document.querySelector('#app');
            if (app && app.__vue__) {
                return Object.keys(app.__vue__.$data || {});
            }
            // 搜索所有的 vue 组件
            let all = document.querySelectorAll('*');
            for (let el of all) {
                if (el.__vue__ && el.__vue__.tableData) {
                    return { foundTableData: el.__vue__.tableData };
                }
                if (el.__vue__ && el.__vue__.list) {
                    return { foundList: el.__vue__.list };
                }
                if (el.__vue__ && el.__vue__.policyList) {
                    return { foundPolicyList: el.__vue__.policyList };
                }
            }
            return null;
        }""")
        print(f"\nApp/Component Vue Data: {app_vue}")

        await browser.close()

asyncio.run(inspect_elements())
