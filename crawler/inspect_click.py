import asyncio
import json
from playwright.async_api import async_playwright

async def inspect_component():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("Navigating...")
        await page.goto("https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014", wait_until="networkidle")
        await asyncio.sleep(4)

        # 深入挖掘 Vue 组件实例
        comp_info = await page.evaluate("""() => {
            let li = document.querySelector('li.item-title');
            if (!li) return "No li.item-title found";
            
            // 找到含有 vue 实例的祖先节点
            let curr = li;
            let res = [];
            while (curr) {
                if (curr.__vue__) {
                    let v = curr.__vue__;
                    res.push({
                        tag: curr.tagName,
                        className: curr.className,
                        data: v.$data,
                        props: v.$props,
                        methods: Object.keys(v.$options.methods || {})
                    });
                }
                curr = curr.parentElement;
            }
            return res;
        }""")

        print("Vue hierarchy info:")
        print(json.dumps(comp_info, ensure_ascii=False, indent=2))

        # 模拟点击并捕获 window.open 或路由跳转
        await page.evaluate("""() => {
            window.__captured_opens = [];
            window.open = function(url, target, features) {
                window.__captured_opens.push({ url: url, target: target, features: features });
            };
        }""")

        li = await page.query_selector("li.item-title")
        if li:
            print("Clicking first item...")
            await li.click()
            await asyncio.sleep(2)

            captured = await page.evaluate("() => window.__captured_opens")
            print("Captured window.open calls:", captured)

        await browser.close()

asyncio.run(inspect_component())
