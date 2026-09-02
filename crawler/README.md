# 政策文档爬虫工具 (SG-Policy Crawler)

专为电网/能源政策、规章制度、政府通知等文档设计的通用爬虫工具。支持文章正文智能提取、表格/条款解析、政策附件（PDF、Word、Excel）自动下载以及多种格式导出（JSON / CSV / JSONL）。

---

## 目录结构

```
crawler/
├── config.py               # 爬虫基础配置（请求头、超时时间、文档格式过滤、路径等）
├── spider.py               # 爬虫核心引擎（Session重试、正文解析、附件提取、多线程并发）
├── sgcc_95598_crawler.py   # 【95598 专用】信息公开目录政策专用自动化爬虫
├── storage.py              # 存储处理器（JSON/CSV/JSONL元数据导出与附件分类归档）
├── main.py                 # 通用命令行入口脚本
├── requirements.txt        # 爬虫相关 Python 依赖
├── README.md               # 使用说明文档
└── data/                   # 爬取结果存储目录
    ├── documents/          # 自动下载的政策源文件 (.pdf, .docx, .xlsx 等)
    └── metadata/           # 提取的元数据结构化数据 (.json, .csv, .jsonl)
```

---

## 安装依赖

```bash
pip install -r crawler/requirements.txt

# 若使用 95598 浏览器自动化模式，安装 Playwright 驱动
playwright install chromium
```

---

## 快速使用

### 1. 爬取国家电网 95598 信息公开目录所有政策

```bash
# 默认使用浏览器自动化模式抓取（可指定省份与页数）
python3 -m crawler.sgcc_95598_crawler --province "北京市" --pages 5

# 可视化窗口调试模式（可观察页面操作与翻页）
python3 -m crawler.sgcc_95598_crawler --province "浙江省" --pages 3 --no-headless

# 接口直连模式
python3 -m crawler.sgcc_95598_crawler --mode api --province "北京市" --pages 5
```

### 2. 通用政策网站抓取（单篇政策或列表页）

```bash
python -m crawler.main --url "https://example.com/policy/notice_123.html"
```

### 2. 抓取政策列表页并批量爬取详情与附件
```bash
python -m crawler.main \
  --url "https://example.com/policy/list" \
  --is-list \
  --limit 20 \
  --workers 4
```

### 3. 指定详情链接正则匹配与输出格式
```bash
python -m crawler.main \
  --url "https://example.com/news" \
  --is-list \
  --pattern r"/news/\d+\.html" \
  --output my_policies \
  --format json
```

### 4. 常用参数一览

| 参数 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `--url` | 目标网页 URL（单页或列表页） | 必填（非 demo 模式） |
| `--is-list` | 声明目标为列表页，先自动解析出各详情页链接再爬取 | `False` |
| `--pattern` | 正则表达式，用于过滤列表页中的目标文章链接 | `None` |
| `--limit` | 列表页抓取详情的最大文章数量限制 | `20` |
| `--workers` | 多线程并发数 | `4` |
| `--delay` | 每次网络请求间隔延迟（秒），防止被封禁 | `1.0` |
| `--no-download-files`| 禁用自动下载文章关联的 PDF/Word/Excel 附件 | `False` (默认自动下载) |
| `--output` | 输出文件名（不含扩展名） | `policies` |
| `--format` | 导出格式：`json`, `jsonl`, `csv`, `all` | `all` |
| `--demo` | 运行内置的测试演示抓取 | - |

---

## 在 Python 代码中作为模块调用

```python
from crawler.spider import PolicyCrawler
from crawler.storage import PolicyStorage

# 初始化爬虫（4线程并发，开启附件自动下载）
crawler = PolicyCrawler(max_workers=4, delay=1.0, download_attachments=True)

# 抓取单篇或多篇文章
results = crawler.crawl_urls([
    "https://example.com/policy/1",
    "https://example.com/policy/2",
])

# 导出数据
storage = PolicyStorage()
storage.save_json(results, "custom_policies.json")
```
