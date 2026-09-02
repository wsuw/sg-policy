#!/usr/bin/env python3
"""
95598 政策文件专用抓取与下载器
目标页面: https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

# 路径定位
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
logger = logging.getLogger("95598-Fetcher")

TARGET_URL = "https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014"


def clean_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = clean.strip()
    return clean[:120] if clean else "未命名政策"


async def fetch_policies():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("请先安装 playwright: pip install playwright && playwright install chromium")
        return

    logger.info(f"==> 启动浏览器，开始抓取 95598 政策文件...")
    logger.info(f"==> 目标页面: {TARGET_URL}")
    logger.info(f"==> 文档保存目录: {DOCS_DIR}")

    intercepted_docs = []
    seen_titles = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        page = await context.new_page()

        # 监听网络响应以捕获所有政策数据接口
        async def on_response(response):
            url = response.url.lower()
            if any(k in url for k in ["policy", "regulations", "querylist", "querydetail", "disclosure", "osgweb"]):
                try:
                    ct = response.headers.get("content-type", "")
                    if "application/json" in ct:
                        data = await response.json()
                        _parse_and_save_api_data(data, response.url, intercepted_docs, seen_titles)
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            logger.info("正在加载页面...")
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=40000)
        except Exception as e:
            logger.warning(f"页面初次加载等待超时，继续解析: {e}")

        await asyncio.sleep(3)

        # 循环翻页解析页面 DOM
        max_pages = 20
        for current_page in range(1, max_pages + 1):
            logger.info(f"--- 正在提取第 {current_page} 页政策文件 ---")

            # 解析当前页面上展示的政策条目
            await _extract_dom_policies(page, intercepted_docs, seen_titles)

            # 尝试点击下一页
            next_btn = await page.query_selector("button.btn-next, .el-pagination .btn-next, text='下一页', a:has-text('下一页')")
            if not next_btn:
                logger.info("未检测到下一页按钮，翻页结束。")
                break

            is_disabled = await next_btn.is_disabled()
            class_str = await next_btn.get_attribute("class") or ""
            if is_disabled or "disabled" in class_str:
                logger.info("已到达最后一页。")
                break

            logger.info("点击进入下一页...")
            await next_btn.click()
            await asyncio.sleep(2.5)

        await browser.close()

    # 导出元数据清单
    meta_file = METADATA_DIR / "95598_policies_P2014.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(intercepted_docs, f, ensure_ascii=False, indent=2)

    logger.info(f"\n==========================================")
    logger.info(f"🎉 抓取任务完成！")
    logger.info(f"📁 政策文件保存位置: {DOCS_DIR}")
    logger.info(f"📊 政策元数据清单: {meta_file}")
    logger.info(f"共获取到 {len(intercepted_docs)} 份政策文件。")
    logger.info(f"==========================================")


def _parse_and_save_api_data(data: Any, source_url: str, docs_list: list, seen_titles: set):
    """解析 API 拦截到的政策并保存文件"""
    items = []
    if isinstance(data, dict):
        d = data.get("data") or data.get("rows") or data.get("list") or data.get("result") or {}
        if isinstance(d, dict):
            items = d.get("list") or d.get("records") or d.get("docs") or d.get("rows") or []
            if not items and (d.get("title") or d.get("policyTitle")):
                items = [d]
        elif isinstance(d, list):
            items = d

    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("policyTitle") or item.get("docName") or item.get("name") or ""
        if not title:
            continue

        title = title.strip()
        if title in seen_titles:
            continue
        seen_titles.add(title)

        publish_date = item.get("publishTime") or item.get("createTime") or item.get("publishDate") or ""
        doc_code = item.get("fileNo") or item.get("docCode") or ""
        content = item.get("content") or item.get("policyContent") or item.get("summary") or ""
        category = item.get("categoryName") or item.get("partName") or "地方性法规及政府规章"

        record = {
            "title": title,
            "doc_code": doc_code,
            "publish_date": publish_date,
            "category": category,
            "content": content,
            "source_url": source_url,
        }
        docs_list.append(record)

        # 保存为政策 Markdown 文件
        save_policy_markdown_file(record)


async def _extract_dom_policies(page, docs_list: list, seen_titles: set):
    """从 DOM 解析卡片条目并保存"""
    selectors = [
        ".policy-item",
        ".policies-item",
        "tr.el-table__row",
        ".list-item",
        ".el-card",
        ".item-content",
        "li",
    ]

    elements = []
    for sel in selectors:
        elements = await page.query_selector_all(sel)
        if len(elements) > 2:
            break

    for el in elements:
        try:
            text = await el.inner_text()
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            if not lines:
                continue

            title = lines[0]
            if len(title) < 4 or title in ["序号", "政策标题", "发布日期", "文号", "操作", "首页", "上一页", "下一页"]:
                continue

            if title in seen_titles:
                continue
            seen_titles.add(title)

            date_str = ""
            for l in lines:
                m = re.search(r"20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}", l)
                if m:
                    date_str = m.group(0)
                    break

            record = {
                "title": title,
                "publish_date": date_str,
                "category": "地方性法规及政府规章 (P2014)",
                "content": "\n\n".join(lines[1:]) if len(lines) > 1 else "",
                "source_url": page.url,
            }
            docs_list.append(record)
            save_policy_markdown_file(record)
        except Exception as e:
            logger.debug(f"解析 DOM 异常: {e}")


def save_policy_markdown_file(record: dict):
    """将政策保存为结构化 Markdown 文件"""
    title = clean_filename(record["title"])
    filename = f"{title}.md"
    file_path = DOCS_DIR / filename

    content_body = record.get("content", "").strip() or "（详见国家电网 95598 原文公告）"

    md_text = f"""# 《{record['title']}》

- **发文字号 / 文号**：{record.get('doc_code') or '暂无'}
- **发布日期**：{record.get('publish_date') or '未知'}
- **所属分类**：{record.get('category') or '政策法规'}
- **来源平台**：国家电网 95598 智能互动网站
- **抓取时间**：{time.strftime('%Y-%m-%d %H:%M:%S')}

---

## 政策正文

{content_body}
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    logger.info(f"✔ 已生成政策文件: {filename}")


if __name__ == "__main__":
    asyncio.run(fetch_policies())
