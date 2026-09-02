#!/usr/bin/env python3
"""
国家电网 95598 政策文件全量下载器
目标:
  1. 遍历 95598 所有政策法规栏目与分类（法律法规、政策文件、公共服务政策库、地方性规程等）
  2. 模拟点击每条政策条目，捕获真实政策 PDF 文件直链 (https://www.95598.cn/omg-static/*.pdf)
  3. 批量下载所有政策 PDF 原文文件，存入 crawler/data/documents/
  4. 生成结构化元数据索引
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

# 路径设置
BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "data" / "documents"
METADATA_DIR = BASE_DIR / "data" / "metadata"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("95598-PDF-Downloader")

# 目标栏目清单
TARGET_PARTS = [
    ("P2014", "地方性法规及政策文件"),
    ("P2011", "国家法律法规"),
    ("P2012", "国务院行政法规"),
    ("P2013", "国家部委规章"),
    ("P2015", "国家电网规章规范"),
    ("P2016", "电价标准及电价表"),
    ("P2017", "供用电服务规范"),
]


def clean_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    clean = re.sub(r'[\\/*?:"<>|\r\n\t]', "", name)
    clean = clean.strip()
    return clean[:120] if clean else "未命名政策"


async def download_pdf_file(context, pdf_url: str, policy_title: str) -> str:
    """下载政策 PDF 原文件"""
    # 修复可能多写了斜杠的 URL
    clean_url = pdf_url.replace("/omg-static//omg-static/", "/omg-static/")
    
    file_base = clean_filename(policy_title)
    if not file_base.lower().endswith(".pdf"):
        file_name = f"{file_base}.pdf"
    else:
        file_name = file_base

    save_path = DOCS_DIR / file_name

    # 若已存在且大小正常，直接跳过
    if save_path.exists() and save_path.stat().st_size > 1024:
        logger.info(f"⏭ 文件已存在，跳过下载: {file_name} ({save_path.stat().st_size // 1024} KB)")
        return str(save_path)

    try:
        resp = await context.request.get(clean_url, timeout=30000)
        if resp.status == 200:
            content = await resp.body()
            with open(save_path, "wb") as f:
                f.write(content)
            size_kb = len(content) // 1024
            logger.info(f"✅ 成功下载政策源文件: {file_name} [{size_kb} KB]")
            return str(save_path)
        else:
            logger.warning(f"下载失败 [{resp.status}]: {clean_url}")
            return ""
    except Exception as e:
        logger.error(f"下载异常 {clean_url}: {e}")
        return ""


async def process_policy_page(context, page, part_no: str, part_name: str, collected_docs: list, seen_urls: set):
    target_url = f"https://www.95598.cn/osgweb/policiesRegulations?partNo={part_no}"
    logger.info(f"\n==================================================")
    logger.info(f"🎯 正在分析栏目: [{part_no}] {part_name}")
    logger.info(f"🔗 页面地址: {target_url}")
    logger.info(f"==================================================")

    try:
        await page.goto(target_url, wait_until="networkidle", timeout=40000)
    except Exception as e:
        logger.warning(f"页面加载等待超时，尝试继续: {e}")

    await asyncio.sleep(4)

    # 注入全局 window.open 拦截器
    await page.evaluate("""() => {
        window.__captured_opens = [];
        window.open = function(url, target, features) {
            window.__captured_opens.push(url);
        };
    }""")

    # 获取子分类 Tab（如 法律法规、政策文件、公共服务政策库 等）
    tabs = await page.query_selector_all(".Advisory_Problem .grid-content, .el-tabs__item")
    tab_count = len(tabs) if tabs else 1

    for t_idx in range(tab_count):
        # 重新获取 Tab 防止 DOM 刷新失效
        current_tabs = await page.query_selector_all(".Advisory_Problem .grid-content, .el-tabs__item")
        if current_tabs and t_idx < len(current_tabs):
            tab_title = (await current_tabs[t_idx].inner_text()).strip()
            logger.info(f"\n>>> 切换至分类 Tab: 【{tab_title}】")
            try:
                await current_tabs[t_idx].click()
                await asyncio.sleep(3)
            except Exception as e:
                logger.warning(f"点击分类 Tab 失败: {e}")
        else:
            tab_title = part_name

        # 遍历翻页提取政策条目与 PDF 链接
        max_pages = 25
        for p_idx in range(1, max_pages + 1):
            logger.info(f"--- 正在扫描【{tab_title}】第 {p_idx} 页政策 ---")

            items = await page.query_selector_all(".sinfo ul li, .fagui li, .policy-list li")
            if not items:
                logger.info("当前页未检测到政策条目，结束本分类。")
                break

            logger.info(f"当前页共有 {len(items)} 条政策")

            for i, item in enumerate(items):
                try:
                    title_text = (await item.inner_text()).strip()
                    if not title_text or len(title_text) < 4:
                        continue

                    # 清空上一次拦截的 URL
                    await page.evaluate("() => { window.__captured_opens = []; }")

                    # 点击政策条目以触发 lookdetail / window.open
                    await item.click()
                    await asyncio.sleep(1.5)

                    captured_urls = await page.evaluate("() => window.__captured_opens")
                    if captured_urls:
                        pdf_url = captured_urls[-1]
                        logger.info(f"📌 捕获到《{title_text}》的 PDF 文件地址: {pdf_url}")

                        # 立即下载该 PDF 文件
                        local_path = await download_pdf_file(context, pdf_url, title_text)

                        doc_info = {
                            "title": title_text,
                            "category": f"{part_name} - {tab_title}",
                            "pdf_url": pdf_url,
                            "local_file": local_path,
                            "source_page": target_url,
                            "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        if pdf_url not in seen_urls:
                            seen_urls.add(pdf_url)
                            collected_docs.append(doc_info)
                    else:
                        logger.warning(f"未捕获到《{title_text}》的 PDF 下载链接")
                except Exception as e:
                    logger.debug(f"处理条目异常: {e}")

            # 检查是否有下一页
            paging_center = await page.query_selector(".paging .center")
            if paging_center:
                page_text = (await paging_center.inner_text()).strip()
                if "/" in page_text:
                    try:
                        cur_p, tot_p = page_text.split("/")
                        if int(cur_p.strip()) >= int(tot_p.strip()):
                            logger.info(f"已达到总页数 ({tot_p.strip()})，当前分类结束")
                            break
                    except Exception:
                        pass

            next_btn = (
                await page.query_selector(".paging .r")
                or await page.query_selector(".paging .el-icon-arrow-right")
                or await page.query_selector("button.btn-next")
            )
            if not next_btn:
                break

            try:
                await next_btn.click()
                await asyncio.sleep(3)
            except Exception:
                break


async def main():
    from playwright.async_api import async_playwright

    logger.info("==================================================")
    logger.info("🚀 启动 95598 政策源文件（PDF）全量精准下载引擎")
    logger.info(f"📂 本地保存目录: {DOCS_DIR}")
    logger.info("==================================================")

    collected_docs = []
    seen_urls = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
        )
        page = await context.new_page()

        for part_no, part_name in TARGET_PARTS:
            await process_policy_page(context, page, part_no, part_name, collected_docs, seen_urls)

        await browser.close()

    # 导出元数据清单
    meta_json = METADATA_DIR / "95598_pdf_documents.json"
    with open(meta_json, "w", encoding="utf-8") as f:
        json.dump(collected_docs, f, ensure_ascii=False, indent=2)

    logger.info("\n==================================================")
    logger.info(f"🎉 全部政策文件下载完成！共下载政策源文件 {len(collected_docs)} 份")
    logger.info(f"📁 政策源文件目录: {DOCS_DIR}")
    logger.info(f"📑 政策索引清单: {meta_json}")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
