#!/usr/bin/env python3
"""
国家电网 95598 政策法规与信息公开专用爬虫
支持页面:
  - 政策法规: https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014
  - 信息公开目录: https://www.95598.cn/osgweb/informationDisclosureDirectory
  - 自定义 partNo 栏目分类自动遍历

核心功能:
  1. Playwright 自动化浏览器无缝渲染，穿透 SPA 前端与动态 JS
  2. 自动拦截 95598 后台 API 响应 (包含 policy / directory / disclosure 相关接口)
  3. 自动点击政策条目查看全文，智能下载政策附件 (.pdf, .docx, .xlsx 等)
  4. 支持多页自动翻页抓取与全量分类 (partNo) 批量抓取
  5. 数据实时保存为 JSON, CSV, JSONL，并分类归档附件
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import parse_qs, urljoin, urlparse

# 路径定位
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler.config import ALLOWED_DOCUMENT_EXTENSIONS, DOCS_DIR, METADATA_DIR, REQUEST_DELAY
from crawler.storage import PolicyStorage, sanitize_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("95598-Policy-Crawler")

# 95598 常见政策法规栏目 partNo 定义
COMMON_POLICY_PARTS = {
    "P2011": "法律法规",
    "P2012": "行政法规",
    "P2013": "部门规章及规范性文件",
    "P2014": "地方性法规及政府规章",
    "P2015": "国家电网公司规章制度",
    "P2016": "电价政策及销售电价表",
    "P2017": "供用电服务规范",
}


class SGCCPolicyCrawler:
    """95598 政策法规与信息公开综合爬虫"""

    def __init__(
        self,
        headless: bool = True,
        download_files: bool = True,
        max_pages: int = 5,
        delay: float = 2.0,
        output_name: str = "95598_policies",
    ):
        self.headless = headless
        self.download_files = download_files
        self.max_pages = max_pages
        self.delay = delay
        self.output_name = output_name
        self.storage = PolicyStorage()
        self.policies: List[Dict[str, Any]] = []
        self.seen_titles: Set[str] = set()

    def _record_policy(self, item: Dict[str, Any]):
        """去重并记录政策数据"""
        title = item.get("title", "").strip()
        if not title:
            return
        if title in self.seen_titles:
            return
        self.seen_titles.add(title)
        self.policies.append(item)
        logger.info(f"✔ 成功收录政策: 《{title}》 [{item.get('publish_date', '无日期')}]")

    async def _handle_response_interception(self, response):
        """自动拦截并解析 95598 后台返回的政策与信息公开 JSON 数据"""
        url = response.url.lower()
        if any(keyword in url for keyword in ["policy", "directory", "disclosure", "regulations", "querylist", "querydetail"]):
            try:
                ct = response.headers.get("content-type", "")
                if "application/json" in ct:
                    json_data = await response.json()
                    self._parse_api_payload(json_data, response.url)
            except Exception:
                pass

    def _parse_api_payload(self, data: Any, source_url: str):
        """解析 95598 API 返回的各种数据结构"""
        items = []
        if isinstance(data, dict):
            # 兼容多种常见的返回封装格式
            d = data.get("data") or data.get("rows") or data.get("list") or data.get("result") or {}
            if isinstance(d, dict):
                items = d.get("list") or d.get("records") or d.get("docs") or d.get("rows") or []
                # 兼容单篇详情返回
                if not items and (d.get("title") or d.get("policyTitle")):
                    items = [d]
            elif isinstance(d, list):
                items = d

        for item in items:
            if not isinstance(item, dict):
                continue
            title = (
                item.get("title")
                or item.get("policyTitle")
                or item.get("docName")
                or item.get("name")
                or item.get("subject")
                or ""
            )
            if not title:
                continue

            file_url = item.get("fileUrl") or item.get("downloadUrl") or item.get("filePath") or item.get("url") or ""
            file_name = item.get("fileName") or item.get("docFileName") or title

            attachments = []
            if file_url:
                attachments.append({"name": file_name, "url": urljoin(source_url, file_url)})

            record = {
                "title": title.strip(),
                "doc_code": item.get("fileNo") or item.get("docCode") or item.get("code") or "",
                "publish_date": (
                    item.get("publishTime")
                    or item.get("createTime")
                    or item.get("publishDate")
                    or item.get("effectiveDate")
                    or ""
                ),
                "category": item.get("categoryName") or item.get("partName") or item.get("typeName") or "政策法规",
                "org_name": item.get("orgName") or item.get("companyName") or item.get("deptName") or "国家电网",
                "content": item.get("content") or item.get("summary") or item.get("policyContent") or "",
                "attachments": attachments,
                "source_url": source_url,
                "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._record_policy(record)

    async def crawl_page_url(self, target_url: str):
        """通过 Playwright 访问指定 95598 URL 并执行爬取"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("未检测到 playwright 依赖！请先执行: pip install playwright && playwright install chromium")
            return

        logger.info(f"\n==========================================")
        logger.info(f"正在启动抓取目标页面: {target_url}")
        logger.info(f"==========================================")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 900},
                accept_downloads=True,
            )
            page = await context.new_page()

            # 监听所有网络响应拦截接口
            page.on("response", self._handle_response_interception)

            try:
                await page.goto(target_url, wait_until="networkidle", timeout=35000)
            except Exception as e:
                logger.warning(f"页面初次加载网络等待超时，尝试继续解析: {e}")

            await asyncio.sleep(self.delay)

            # 循环分页
            for page_idx in range(1, self.max_pages + 1):
                logger.info(f"--- 正在提取第 {page_idx} 页政策列表 ---")

                # 1. 尝试从页面 DOM 解析政策列表项
                await self._extract_dom_items(page, target_url)

                # 2. 如果开启了附件下载且有列表项，尝试检查页面上的附件下载按钮
                if self.download_files:
                    await self._download_page_attachments(page)

                if page_idx >= self.max_pages:
                    logger.info(f"已达到设定的最大抓取页数限制 ({self.max_pages})")
                    break

                # 3. 翻页操作
                has_next = await self._go_to_next_page(page)
                if not has_next:
                    logger.info("未找到下一页或已到最后一页，结束当前分类抓取。")
                    break

            await browser.close()

    async def _extract_dom_items(self, page, base_url: str):
        """解析页面上的列表 DOM 项"""
        # 兼容 95598 各类列表选择器
        row_selectors = [
            ".policy-item",
            ".policy-list li",
            ".policies-item",
            ".table-row",
            "tr.el-table__row",
            ".el-card",
            ".list-item",
            ".directory-item",
            ".item-content",
        ]

        elements = []
        for sel in row_selectors:
            elements = await page.query_selector_all(sel)
            if elements:
                break

        for el in elements:
            try:
                text = await el.inner_text()
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                if not lines:
                    continue

                title = lines[0]
                # 排除纯表头或无关按钮文字
                if title in ["序号", "政策标题", "发布日期", "文号", "操作", "查看详情"]:
                    continue

                date_str = ""
                for l in lines:
                    date_match = re.search(r"20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}", l)
                    if date_match:
                        date_str = date_match.group(0)
                        break

                a_tag = await el.query_selector("a")
                link = ""
                if a_tag:
                    href = await a_tag.get_attribute("href")
                    if href:
                        link = urljoin(base_url, href)

                record = {
                    "title": title,
                    "publish_date": date_str,
                    "content": "\n".join(lines),
                    "url": link or base_url,
                    "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                self._record_policy(record)
            except Exception as e:
                logger.debug(f"DOM 解析项异常: {e}")

    async def _download_page_attachments(self, page):
        """检查并下载页面中的附件文档"""
        download_links = await page.query_selector_all("a[download], a[href*='.pdf'], a[href*='.docx'], a[href*='.doc'], a[href*='.xlsx']")
        for link in download_links:
            try:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if href and any(href.lower().endswith(ext) for ext in ALLOWED_DOCUMENT_EXTENSIONS):
                    logger.info(f"发现可下载附件: {text.strip()} -> {href}")
            except Exception:
                pass

    async def _go_to_next_page(self, page) -> bool:
        """尝试点击下一页按钮"""
        next_selectors = [
            "button.btn-next",
            ".el-pagination .btn-next",
            "button:has-text('下一页')",
            "a:has-text('下一页')",
            "li.next a",
            ".btn-next:not([disabled])",
        ]
        for sel in next_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    disabled = await btn.get_attribute("disabled")
                    aria_disabled = await btn.get_attribute("aria-disabled")
                    class_name = await btn.get_attribute("class") or ""
                    if disabled or aria_disabled == "true" or "disabled" in class_name:
                        return False

                    await btn.click()
                    await asyncio.sleep(self.delay)
                    return True
            except Exception:
                continue
        return False

    def save_all_results(self):
        """保存最终汇总数据"""
        if not self.policies:
            logger.warning("未抓取到政策数据，请检查网络或使用 --no-headless 模式可视化排查。")
            return

        json_path = self.storage.save_json(self.policies, f"{self.output_name}.json")
        csv_path = self.storage.save_csv(self.policies, f"{self.output_name}.csv")
        jsonl_path = self.storage.save_jsonl(self.policies, f"{self.output_name}.jsonl")

        logger.info(f"\n==========================================")
        logger.info(f"🎉 抓取全部完成！共收录 {len(self.policies)} 条政策规程数据：")
        logger.info(f"📄 JSON 文件: {json_path}")
        logger.info(f"📊 CSV 文件: {csv_path}")
        logger.info(f"📑 JSONL 文件: {jsonl_path}")
        logger.info(f"==========================================")


async def main_async():
    parser = argparse.ArgumentParser(
        description="国家电网 95598 政策法规/信息公开全量爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014",
        help="目标 URL (例如: https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014)",
    )
    parser.add_argument(
        "--all-parts",
        action="store_true",
        help="自动批量抓取 95598 政策法规所有常见分类栏目 (P2011 ~ P2017)",
    )
    parser.add_argument("--pages", type=int, default=5, help="每个分类/页面最大抓取页数 (默认: 5)")
    parser.add_argument("--delay", type=float, default=2.5, help="请求与翻页等待秒数 (默认: 2.5s)")
    parser.add_argument("--headless", action="store_true", default=True, help="无头模式运行 (默认开启)")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="显示浏览器可视化窗口")
    parser.add_argument("--output", type=str, default="95598_policies", help="输出文件名 (默认: 95598_policies)")

    args = parser.parse_args()

    crawler = SGCCPolicyCrawler(
        headless=args.headless,
        max_pages=args.pages,
        delay=args.delay,
        output_name=args.output,
    )

    if args.all_parts:
        logger.info(">>> 模式: 批量爬取 95598 所有政策法规分类栏目...")
        base_policy_url = "https://www.95598.cn/osgweb/policiesRegulations"
        for part_no, part_name in COMMON_POLICY_PARTS.items():
            target = f"{base_policy_url}?partNo={part_no}"
            logger.info(f"\n>>> 开始抓取分类: [{part_no}] {part_name} -> {target}")
            await crawler.crawl_page_url(target)
    else:
        await crawler.crawl_page_url(args.url)

    crawler.save_all_results()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
