#!/usr/bin/env python3
"""
95598 政策法规全量自动化爬虫
目标: 爬取 https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014 下的所有政策文件
包括正文全文提取与附件下载
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
from urllib.parse import urljoin

# 路径定位
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DOCS_DIR = BASE_DIR / "data" / "documents"
METADATA_DIR = BASE_DIR / "data" / "metadata"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("95598-Crawler")

TARGET_URL = "https://www.95598.cn/osgweb/policiesRegulations?partNo=P2014"


def clean_filename(name: str) -> str:
    """清理文件名非法字符"""
    clean = re.sub(r'[\\/*?:"<>|\r\n\t]', "", name)
    clean = clean.strip()
    return clean[:100] if clean else "未命名政策"


async def download_file_by_url(context, url: str, filename: str) -> Path:
    """下载附件文件"""
    save_path = DOCS_DIR / clean_filename(filename)
    try:
        page = await context.new_page()
        async with page.expect_download() as download_info:
            await page.goto(url)
        download = await download_info.value
        await download.save_as(save_path)
        await page.close()
        logger.info(f"✔ 成功下载附件: {save_path.name}")
        return save_path
    except Exception as e:
        logger.warning(f"下载附件失败 {url}: {e}")
        return None


def save_policy_document(record: dict) -> Path:
    """保存单篇政策为独立的 Markdown 文件"""
    title = clean_filename(record["title"])
    filename = f"{title}.md"
    file_path = DOCS_DIR / filename

    content_text = record.get("content", "").strip() or "（详见国家电网 95598 原文）"
    
    attachments_md = ""
    if record.get("attachments"):
        attachments_md = "\n### 附件列表\n" + "\n".join(
            [f"- [{a['name']}]({a.get('local_path', a.get('url'))})" for a in record["attachments"]]
        )

    md_content = f"""# 《{record['title']}》

- **发文字号**：{record.get('doc_code') or '暂无'}
- **发布日期**：{record.get('publish_date') or '未知'}
- **政策分类**：{record.get('category') or '政策法规'}
- **发布机构/地区**：{record.get('org_name') or '国家电网'}
- **数据来源**：国家电网 95598 (https://www.95598.cn/osgweb/policiesRegulations)
- **抓取时间**：{time.strftime('%Y-%m-%d %H:%M:%S')}

---

## 政策正文

{content_text}

{attachments_md}
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    logger.info(f"✔ 已保存政策文档: {file_path.name}")
    return file_path


async def crawl_95598():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("请先安装 playwright: pip install playwright && playwright install chromium")
        return

    logger.info("==================================================")
    logger.info("🚀 启动 95598 政策法规自动化采集引擎")
    logger.info(f"🎯 目标链接: {TARGET_URL}")
    logger.info(f"📂 文档落地目录: {DOCS_DIR}")
    logger.info("==================================================")

    all_policies = []
    seen_titles = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            accept_downloads=True,
        )
        page = await context.new_page()

        # 监听并拦截响应中的政策解密数据（若有）
        async def on_response(response):
            url = response.url.lower()
            if any(k in url for k in ["policy", "regulations", "querylist", "querydetail", "content"]):
                try:
                    ct = response.headers.get("content-type", "")
                    if "application/json" in ct:
                        data = await response.json()
                        _parse_intercepted_json(data, all_policies, seen_titles)
                except Exception:
                    pass

        page.on("response", on_response)

        logger.info("正在打开 95598 政策法规页面...")
        try:
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=45000)
        except Exception as e:
            logger.warning(f"页面网络空闲等待超时，继续后续解析: {e}")

        await asyncio.sleep(4)

        # 获取所有的分类 Tab（如 法律法规、政策文件、公共服务政策库 等）
        tab_selectors = await page.query_selector_all(".Advisory_Problem .grid-content, .el-tabs__item, .tabs li")
        tab_names = []
        for t in tab_selectors:
            txt = (await t.inner_text()).strip()
            if txt and len(txt) < 20:
                tab_names.append(txt)

        logger.info(f"检测到 {len(tab_names)} 个分类 Tab: {tab_names}")

        # 如果没有识别到 tab，就使用默认流程
        tabs_to_process = tab_selectors if tab_selectors else [None]

        for tab_idx, tab_elem in enumerate(tabs_to_process):
            tab_title = tab_names[tab_idx] if tab_idx < len(tab_names) else "政策法规"
            if tab_elem:
                logger.info(f"\n>>> 正在切换至分类 Tab: 【{tab_title}】")
                try:
                    await tab_elem.click()
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.warning(f"点击 Tab 失败: {e}")

            # 在当前分类下进行翻页抓取
            max_pages = 30
            for current_page_no in range(1, max_pages + 1):
                logger.info(f"--- 正在提取【{tab_title}】第 {current_page_no} 页 ---")

                # 获取列表中的政策项
                items = await page.query_selector_all(".fagui .sinfo ul li, .fagui li, .sinfo li, .policy-list li, tr.el-table__row")
                if not items:
                    # 尝试查找包含文本的列表容器
                    items = await page.query_selector_all(".sinfo ul > *")

                logger.info(f"当前页找到 {len(items)} 条政策条目")
                if not items:
                    break

                for i, item in enumerate(items):
                    try:
                        item_text = await item.inner_text()
                        lines = [l.strip() for l in item_text.split("\n") if l.strip()]
                        if not lines:
                            continue

                        title = lines[0]
                        if title in ["序号", "政策标题", "发布日期", "文号", "操作"]:
                            continue

                        # 过滤导航或重复
                        if title in seen_titles:
                            continue

                        date_str = ""
                        for l in lines:
                            m = re.search(r"20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}", l)
                            if m:
                                date_str = m.group(0)
                                break

                        doc_code = ""
                        for l in lines:
                            if any(k in l for k in ["号", "字", "〔", "【", "第"]):
                                doc_code = l
                                break

                        # 尝试点击条目查看详情
                        logger.info(f"正在读取条目详情: 《{title}》")
                        detail_content = ""
                        attachments = []

                        # 检查条目内部是否有可点击链接
                        click_target = await item.query_selector("a, span, .title, strong") or item
                        try:
                            # 点击打开详情弹窗或页面
                            await click_target.click()
                            await asyncio.sleep(2)

                            # 检查弹窗或详情容器
                            detail_modal = await page.query_selector(".el-dialog, .modal, .detail-box, .fagui-detail, .content-detail")
                            if detail_modal and await detail_modal.is_visible():
                                detail_content = await detail_modal.inner_text()
                                # 检查弹窗内的附件链接
                                att_links = await detail_modal.query_selector_all("a[href*='.pdf'], a[href*='.doc'], a[href*='.docx'], a[href*='.xlsx']")
                                for att in att_links:
                                    att_href = await att.get_attribute("href")
                                    att_name = (await att.inner_text()).strip() or "附件文档"
                                    if att_href:
                                        attachments.append({"name": att_name, "url": att_href})

                                # 关闭弹窗
                                close_btn = await page.query_selector(".el-dialog__close, .el-dialog__headerbtn, .close, text='关闭'")
                                if close_btn:
                                    await close_btn.click()
                                    await asyncio.sleep(1)
                            else:
                                detail_content = "\n\n".join(lines[1:]) if len(lines) > 1 else ""
                        except Exception as e:
                            detail_content = "\n\n".join(lines[1:]) if len(lines) > 1 else ""

                        record = {
                            "title": title,
                            "category": tab_title,
                            "publish_date": date_str,
                            "doc_code": doc_code,
                            "org_name": "国家电网",
                            "content": detail_content,
                            "attachments": attachments,
                            "source_url": TARGET_URL,
                        }

                        seen_titles.add(title)
                        all_policies.append(record)

                        # 保存文件
                        save_policy_document(record)

                    except Exception as e:
                        logger.debug(f"处理条目异常: {e}")

                # 寻找下一页
                paging_center = await page.query_selector(".paging .center")
                if paging_center:
                    page_text = (await paging_center.inner_text()).strip()
                    logger.info(f"页码状态: {page_text}")
                    if "/" in page_text:
                        try:
                            cur_p, tot_p = page_text.split("/")
                            if int(cur_p.strip()) >= int(tot_p.strip()):
                                logger.info(f"已到达总页数 ({tot_p.strip()})，当前分类结束")
                                break
                        except Exception:
                            pass

                next_btn = (
                    await page.query_selector(".paging .r")
                    or await page.query_selector(".paging .el-icon-arrow-right")
                    or await page.query_selector("button.btn-next")
                    or await page.query_selector(".btn-next")
                )
                if not next_btn:
                    logger.info("未找到下一页按钮，当前分类结束")
                    break

                try:
                    await next_btn.click()
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.warning(f"点击下一页失败: {e}")
                    break


        await browser.close()

    # 导出元数据
    meta_json = METADATA_DIR / "95598_policies.json"
    with open(meta_json, "w", encoding="utf-8") as f:
        json.dump(all_policies, f, ensure_ascii=False, indent=2)

    logger.info("==================================================")
    logger.info(f"🎉 爬取完成！共生成政策文件 {len(all_policies)} 份")
    logger.info(f"📁 政策文件存储目录: {DOCS_DIR}")
    logger.info(f"📑 元数据清单: {meta_json}")
    logger.info("==================================================")


def _parse_intercepted_json(data: Any, docs_list: list, seen_titles: set):
    """解析网络拦截到的政策 JSON"""
    items = []
    if isinstance(data, dict):
        d = data.get("data") or data.get("rows") or data.get("list") or data.get("result") or {}
        if isinstance(d, dict):
            items = d.get("list") or d.get("records") or d.get("docs") or d.get("rows") or []
        elif isinstance(d, list):
            items = d

    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("policyTitle") or item.get("docName") or item.get("name") or ""
        if not title or title.strip() in seen_titles:
            continue

        title = title.strip()
        seen_titles.add(title)

        record = {
            "title": title,
            "category": item.get("categoryName") or item.get("partName") or "政策法规",
            "publish_date": item.get("publishTime") or item.get("createTime") or item.get("publishDate") or "",
            "doc_code": item.get("fileNo") or item.get("docCode") or "",
            "org_name": item.get("orgName") or item.get("companyName") or "国家电网",
            "content": item.get("content") or item.get("policyContent") or item.get("summary") or "",
            "source_url": TARGET_URL,
        }
        docs_list.append(record)
        save_policy_document(record)


if __name__ == "__main__":
    asyncio.run(crawl_95598())
