#!/usr/bin/env python3
"""
政策知识库通用爬虫入口脚本
使用示例:
    1. 抓取单篇详情页及附件:
       python -m crawler.main --url "https://example.com/policy/123.html"

    2. 抓取政策列表页并递归抓取详情与文档:
       python -m crawler.main --url "https://example.com/policies" --is-list --limit 10

    3. 运行本地示例/模拟测试:
       python -m crawler.main --demo
"""

import argparse
import sys
from pathlib import Path

# 确保父目录在 sys.path 中，以便支持模块导入
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler.spider import PolicyCrawler, logger
from crawler.storage import PolicyStorage


def run_demo():
    """运行测试/模拟抓取示例"""
    logger.info(">>> 启动示例演示爬虫...")
    crawler = PolicyCrawler(max_workers=2, delay=0.5, download_attachments=False)
    
    # 示例测试抓取国家能源局或公开政策站点
    sample_urls = [
        "http://www.nea.gov.cn/",
    ]
    logger.info(f"正在抓取示例站点: {sample_urls}")
    results = crawler.crawl_urls(sample_urls)
    
    storage = PolicyStorage()
    json_path = storage.save_json(results, "demo_policies.json")
    logger.info(f"演示数据已保存至: {json_path}")
    logger.info(f"共抓取 {len(results)} 条数据")


def main():
    parser = argparse.ArgumentParser(
        description="政策与规程通用网络爬虫 (SG-Policy Crawler)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", type=str, help="目标网页 URL (文章详情页或列表页)")
    parser.add_argument("--is-list", action="store_true", help="指定目标 URL 为列表页，自动提取详情页链接")
    parser.add_argument("--pattern", type=str, default=None, help="匹配列表页详情链接的正则表达式")
    parser.add_argument("--limit", type=int, default=20, help="最多抓取的详情页数量 (默认 20)")
    parser.add_argument("--workers", type=int, default=4, help="并发爬取线程数 (默认 4)")
    parser.add_argument("--delay", type=float, default=1.0, help="请求间隔延迟秒数 (默认 1.0s)")
    parser.add_argument("--no-download-files", action="store_true", help="禁用附件文档 (pdf, docx 等) 自动下载")
    parser.add_argument("--output", type=str, default="policies", help="输出文件名前缀 (默认 policies)")
    parser.add_argument("--format", choices=["json", "jsonl", "csv", "all"], default="all", help="输出格式")
    parser.add_argument("--demo", action="store_true", help="运行内置演示示例")

    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    if not args.url:
        logger.error("请提供目标 URL (--url) 或运行测试示例 (--demo)")
        parser.print_help()
        sys.exit(1)

    crawler = PolicyCrawler(
        max_workers=args.workers,
        delay=args.delay,
        download_attachments=not args.no_download_files,
    )

    urls_to_crawl = []
    if args.is_list:
        logger.info(f"正在从列表页分析目标链接: {args.url}")
        extracted_links = crawler.extract_links_from_list_page(args.url, link_pattern=args.pattern)
        urls_to_crawl = extracted_links[: args.limit]
        logger.info(f"根据限制，本次将抓取前 {len(urls_to_crawl)} 个详情链接")
    else:
        urls_to_crawl = [args.url]

    if not urls_to_crawl:
        logger.warning("未找到待抓取的 URL，退出")
        return

    results = crawler.crawl_urls(urls_to_crawl)
    logger.info(f"抓取完成！成功获取 {len(results)} 篇文档内容。")

    # 数据导出与存储
    storage = PolicyStorage()
    base_name = args.output
    if args.format in ("json", "all"):
        p = storage.save_json(results, f"{base_name}.json")
        logger.info(f"JSON 结果已保存至: {p}")
    if args.format in ("jsonl", "all"):
        p = storage.save_jsonl(results, f"{base_name}.jsonl")
        logger.info(f"JSONL 结果已保存至: {p}")
    if args.format in ("csv", "all"):
        p = storage.save_csv(results, f"{base_name}.csv")
        logger.info(f"CSV 结果已保存至: {p}")


if __name__ == "__main__":
    main()
