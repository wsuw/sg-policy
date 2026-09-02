import os
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "documents"
METADATA_DIR = DATA_DIR / "metadata"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

# 默认请求配置
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

REQUEST_TIMEOUT = 15  # 请求超时时间（秒）
MAX_RETRIES = 3       # 最大重试次数
RETRY_BACKOFF = 1.5   # 重试指数退避因子
REQUEST_DELAY = 1.0   # 请求间隔延迟（秒），防止被封禁

# 支持下载的政策文件扩展名
ALLOWED_DOCUMENT_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".csv"
}
