#!/usr/bin/env python3
"""
95598 全量栏目（P2011-P2017）政策文件深度抓取器
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

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
logger = logging.getLogger("95598-AllParts")

PARTS = [
    ("P2011", "国家法律法规"),
    ("P2012", "国务院行政法规"),
    ("P2013", "国家部委规章"),
    ("P2014", "地方性法规及政策文件"),
    ("P2015", "国家电网规章规范"),
    ("P2016", "电价标准及电价表"),
    ("P2017", "供用电服务规范"),
]


def clean_filename(name: str) -> str:
    clean = re.sub(r'[\\/*?:"<>|\r\n\t]', "", name)
    clean = clean.strip()
    return clean[:100] if clean else "未命名政策"


def save_policy_md(record: dict) -> Path:
    title = clean_filename(record["title"])
    filename = f"{title}.md"
    file_path = DOCS_DIR / filename

    content_text = record.get("content", "").strip() or "（详见国家电网 95598 原文）"

    md_content = f"""# 《{record['title']}》

- **发文字号 / 文号**：{record.get('doc_code') or '暂无'}
- **发布日期**：{record.get('publish_date') or '未知'}
- **所属栏目**：{record.get('category') or '政策法规'}
- **所属省份/单位**：{record.get('province') or '国家电网'}
- **数据来源**：国家电网 95598 ({record.get('source_url')})
- **抓取时间**：{time.strftime('%Y-%m-%d %H:%M:%S')}

---

## 政策正文

{content_text}
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    logger.info(f"✔ 已保存/更新政策文件: {filename}")
    return file_path


async def crawl_part(page, part_no: str, part_name: str, all_policies: list, seen_titles: set):
    target_url = f"https://www.95598.cn/osgweb/policiesRegulations?partNo={part_no}"
    logger.info(f"\n==================================================")
    logger.info(f"🚀 开始采集栏目: [{part_no}] {part_name} -> {target_url}")
    logger.info(f"==================================================")

    try:
        await page.goto(target_url, wait_until="networkidle", timeout=35000)
    except Exception as e:
        logger.warning(f"页面加载等待超时，继续解析: {e}")

    await asyncio.sleep(4)

    # 检查是否有子分类 Tab
    tabs = await page.query_selector_all(".Advisory_Problem .grid-content, .el-tabs__item")
    tab_count = len(tabs) if tabs else 1

    for t_idx in range(tab_count):
        # 重新定位 Tab
        if tabs:
            current_tabs = await page.query_selector_all(".Advisory_Problem .grid-content, .el-tabs__item")
            if t_idx < len(current_tabs):
                tab_text = (await current_tabs[t_idx].inner_text()).strip()
                logger.info(f"\n>>> 切换子分类 Tab: 【{tab_text}】")
                try:
                    await current_tabs[t_idx].click()
                    await asyncio.sleep(3)
                except Exception as e:
                    logger.warning(f"点击子分类失败: {e}")
            else:
                tab_text = part_name
        else:
            tab_text = part_name

        # 遍历翻页
        max_pages = 25
        for p_idx in range(1, max_pages + 1):
            logger.info(f"--- 正在提取【{tab_text}】第 {p_idx} 页 ---")

            items = await page.query_selector_all(".fagui .sinfo ul li, .fagui li, .sinfo li, .policy-list li")
            if not items:
                logger.info("当前页无政策数据，结束本子分类")
                break

            for el in items:
                try:
                    txt = await el.inner_text()
                    lines = [l.strip() for l in txt.split("\n") if l.strip()]
                    if not lines:
                        continue

                    title = lines[0]
                    if len(title) < 4 or title in ["序号", "政策标题", "发布日期", "文号", "操作"]:
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

                    doc_code = ""
                    for l in lines:
                        if any(k in l for k in ["号", "字", "〔", "【", "第"]):
                            doc_code = l
                            break

                    record = {
                        "title": title,
                        "category": f"{part_name} - {tab_text}",
                        "publish_date": date_str,
                        "doc_code": doc_code,
                        "province": "国家电网",
                        "content": "\n\n".join(lines[1:]) if len(lines) > 1 else "",
                        "source_url": target_url,
                        "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    all_policies.append(record)
                    save_policy_md(record)

                except Exception as e:
                    logger.debug(f"解析条目异常: {e}")

            # 检查翻页
            paging_center = await page.query_selector(".paging .center")
            if paging_center:
                page_text = (await paging_center.inner_text()).strip()
                if "/" in page_text:
                    try:
                        cur_p, tot_p = page_text.split("/")
                        if int(cur_p.strip()) >= int(tot_p.strip()):
                            logger.info(f"已达到最大页 ({tot_p.strip()})，结束本子分类")
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
                await asyncio.sleep(2.5)
            except Exception:
                break


async def main_all():
    from playwright.async_api import async_playwright

    all_policies = []
    seen_titles = set()

    # 预加载已有政策
    meta_json = METADATA_DIR / "95598_policies.json"
    if meta_json.exists():
        try:
            with open(meta_json, "r", encoding="utf-8") as f:
                existing = json.load(f)
                for item in existing:
                    if item.get("title"):
                        seen_titles.add(item["title"])
                        all_policies.append(item)
        except Exception:
            pass

    logger.info(f"已有政策库基准数量: {len(all_policies)} 篇")

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

        for part_no, part_name in PARTS:
            await crawl_part(page, part_no, part_name, all_policies, seen_titles)

        await browser.close()

    # 保存最终全量元数据
    with open(meta_json, "w", encoding="utf-8") as f:
        json.dump(all_policies, f, ensure_ascii=False, indent=2)

    logger.info("\n==================================================")
    logger.info(f"🎉 全部栏目抓取完成！当前政策文件总库共计: {len(all_policies)} 篇")
    logger.info(f"📁 政策文件存储目录: {DOCS_DIR}")
    logger.info(f"📑 元数据清单: {meta_json}")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(main_all())
