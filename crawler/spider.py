import html.parser
import json
import logging
import os
import re
import ssl
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse
import urllib.request

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util import Retry
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from fake_useragent import UserAgent
    ua = UserAgent()
except Exception:
    ua = None

from crawler.config import (
    ALLOWED_DOCUMENT_EXTENSIONS,
    DEFAULT_HEADERS,
    MAX_RETRIES,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
)
from crawler.storage import PolicyStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("PolicyCrawler")


class SimpleHTMLParser(html.parser.HTMLParser):
    """纯标准库实现的简单 HTML 解析器（当未安装 bs4 时的回退方案）"""

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.title = ""
        self.in_title = False
        self.text_chunks = []
        self.links: List[Tuple[str, str]] = []  # (href, text)
        self.current_a_href = None
        self.current_a_text = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        if tag.lower() == "title":
            self.in_title = True
        elif tag.lower() == "a":
            self.current_a_href = attr_dict.get("href")
            self.current_a_text = []
        elif tag.lower() in ("p", "br", "div", "h1", "h2", "h3", "h4", "tr"):
            self.text_chunks.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False
        elif tag.lower() == "a":
            if self.current_a_href:
                full_url = urljoin(self.base_url, self.current_a_href)
                link_text = "".join(self.current_a_text).strip()
                self.links.append((full_url, link_text))
            self.current_a_href = None
            self.current_a_text = []

    def handle_data(self, data):
        if self.in_title:
            self.title += data.strip()
        if self.current_a_href:
            self.current_a_text.append(data)
        self.text_chunks.append(data)


class PolicyCrawler:
    """政策与文档通用网络抓取器"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        max_workers: int = 4,
        delay: float = REQUEST_DELAY,
        download_attachments: bool = True,
    ):
        self.base_url = base_url
        self.max_workers = max_workers
        self.delay = delay
        self.download_attachments = download_attachments
        self.storage = PolicyStorage()
        self.visited_urls: Set[str] = set()

        if HAS_REQUESTS:
            self.session = requests.Session()
            retries = Retry(
                total=MAX_RETRIES,
                backoff_factor=RETRY_BACKOFF,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(
                max_retries=retries,
                pool_connections=max_workers * 2,
                pool_maxsize=max_workers * 2,
            )
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
        else:
            self.session = None

    def _get_headers(self) -> Dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        if ua:
            try:
                headers["User-Agent"] = ua.random
            except Exception:
                pass
        return headers

    def fetch_page_content(self, url: str) -> Optional[Tuple[str, bytes]]:
        """获取页面 HTML 文本和原始字节"""
        time.sleep(self.delay)
        headers = self._get_headers()

        if HAS_REQUESTS and self.session:
            try:
                resp = self.session.get(
                    url,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                    verify=False,
                )
                if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
                    resp.encoding = resp.apparent_encoding or "utf-8"
                if resp.status_code == 200:
                    return resp.text, resp.content
                logger.warning(f"请求失败 [{resp.status_code}]: {url}")
                return None
            except Exception as e:
                logger.error(f"请求异常 {url}: {e}")
                return None
        else:
            # 使用 Python 标准库 urllib
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=ctx) as response:
                    raw = response.read()
                    charset = "utf-8"
                    content_type = response.headers.get("Content-Type", "")
                    if "charset=" in content_type:
                        charset = content_type.split("charset=")[-1].strip()
                    try:
                        text = raw.decode(charset)
                    except Exception:
                        text = raw.decode("utf-8", errors="replace")
                    return text, raw
            except Exception as e:
                logger.error(f"urllib 请求异常 {url}: {e}")
                return None

    def extract_article(self, url: str, html_text: str) -> Dict[str, Any]:
        """从网页 HTML 中解析文章详情及附件链接"""
        title = ""
        content = ""
        attachments = []

        if HAS_BS4:
            soup = BeautifulSoup(html_text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
                tag.decompose()

            title_tag = soup.find("h1") or soup.find("h2") or soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)

            main_content = (
                soup.find("article")
                or soup.find("div", class_=re.compile(r"content|article|detail|main|news-content|text", re.I))
                or soup.find("div", id=re.compile(r"content|article|detail|main|text", re.I))
                or soup.body
            )
            if main_content:
                paragraphs = [p.get_text(strip=True) for p in main_content.find_all(["p", "div", "h2", "h3", "h4", "table"])]
                content = "\n\n".join([p for p in paragraphs if p])
            else:
                content = soup.get_text(separator="\n", strip=True)

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                full_link = urljoin(url, href)
                parsed_path = urlparse(full_link).path.lower()
                if any(parsed_path.endswith(ext) for ext in ALLOWED_DOCUMENT_EXTENSIONS):
                    link_text = a_tag.get_text(strip=True) or parsed_path.split("/")[-1]
                    attachments.append({"name": link_text, "url": full_link})
        else:
            # 标准库解析
            parser = SimpleHTMLParser(base_url=url)
            try:
                parser.feed(html_text)
            except Exception:
                pass
            title = parser.title
            content = re.sub(r"\n\s*\n+", "\n\n", "".join(parser.text_chunks)).strip()
            for full_link, link_text in parser.links:
                parsed_path = urlparse(full_link).path.lower()
                if any(parsed_path.endswith(ext) for ext in ALLOWED_DOCUMENT_EXTENSIONS):
                    attachments.append({
                        "name": link_text or parsed_path.split("/")[-1],
                        "url": full_link,
                    })

        # 尝试提取发布时间
        pub_date = ""
        date_pattern = r"\b(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2}日?)\b"
        date_match = re.search(date_pattern, html_text)
        if date_match:
            pub_date = date_match.group(1).replace("年", "-").replace("月", "-").replace("日", "")

        return {
            "title": title,
            "url": url,
            "publish_date": pub_date,
            "content": content,
            "attachments": attachments,
            "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def download_attachment(self, attachment_url: str, fallback_name: str) -> Optional[str]:
        """下载附件文档并保存到本地"""
        try:
            time.sleep(self.delay)
            res = self.fetch_page_content(attachment_url)
            if res:
                _, raw_bytes = res
                filename = fallback_name
                if not any(filename.lower().endswith(ext) for ext in ALLOWED_DOCUMENT_EXTENSIONS):
                    url_suffix = Path(urlparse(attachment_url).path).suffix
                    filename += (url_suffix if url_suffix else ".bin")

                saved_path = self.storage.save_document(raw_bytes, filename)
                logger.info(f"成功下载附件: {saved_path.name}")
                return str(saved_path)
            return None
        except Exception as e:
            logger.error(f"下载附件异常 {attachment_url}: {e}")
            return None

    def crawl_article(self, url: str) -> Optional[Dict[str, Any]]:
        """抓取单篇详情文章"""
        if url in self.visited_urls:
            return None
        self.visited_urls.add(url)

        logger.info(f"正在抓取详情页: {url}")
        res = self.fetch_page_content(url)
        if not res:
            return None

        html_text, _ = res
        article = self.extract_article(url, html_text)

        # 下载附件
        if self.download_attachments and article.get("attachments"):
            downloaded_files = []
            for att in article["attachments"]:
                saved = self.download_attachment(att["url"], att["name"])
                if saved:
                    downloaded_files.append({"name": att["name"], "local_path": saved, "url": att["url"]})
            article["downloaded_files"] = downloaded_files

        return article

    def crawl_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """批量多线程抓取一组 URL"""
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_url = {executor.submit(self.crawl_article, u): u for u in urls}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    data = future.result()
                    if data:
                        results.append(data)
                except Exception as e:
                    logger.error(f"处理任务异常 {url}: {e}")
        return results

    def extract_links_from_list_page(self, list_url: str, link_pattern: Optional[str] = None) -> List[str]:
        """从列表页中提取文章详情页链接"""
        logger.info(f"正在解析列表页: {list_url}")
        res = self.fetch_page_content(list_url)
        if not res:
            return []

        html_text, _ = res
        links = set()

        if HAS_BS4:
            soup = BeautifulSoup(html_text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                full_url = urljoin(list_url, href)
                if full_url.startswith("javascript:") or full_url.startswith("#"):
                    continue
                if link_pattern:
                    if re.search(link_pattern, full_url):
                        links.add(full_url)
                else:
                    if any(k in full_url.lower() for k in ["article", "content", "news", "policy", "detail", ".html", ".htm"]):
                        links.add(full_url)
        else:
            parser = SimpleHTMLParser(base_url=list_url)
            try:
                parser.feed(html_text)
            except Exception:
                pass
            for full_url, _ in parser.links:
                if full_url.startswith("javascript:") or full_url.startswith("#"):
                    continue
                if link_pattern:
                    if re.search(link_pattern, full_url):
                        links.add(full_url)
                else:
                    if any(k in full_url.lower() for k in ["article", "content", "news", "policy", "detail", ".html", ".htm"]):
                        links.add(full_url)

        logger.info(f"从列表页提取到 {len(links)} 个候选详情链接")
        return list(links)
