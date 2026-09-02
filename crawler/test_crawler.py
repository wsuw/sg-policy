import unittest
from pathlib import Path
from crawler.spider import PolicyCrawler
from crawler.storage import PolicyStorage

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>国家电网某项新规指导意见（试行）</title>
</head>
<body>
    <h1>国家电网某项新规指导意见（试行）</h1>
    <div class="pub-info">发布日期：2024-05-18</div>
    <div class="content">
        <p>第一条 为了进一步规范电力市场交易秩序，制定本办法。</p>
        <p>第二条 本办法适用于各级电力调度机构及发电企业。</p>
        <p>附件：</p>
        <a href="/files/20240518_guideline.docx">《指导意见执行细则.docx》</a>
        <a href="/files/20240518_summary.pdf">《政策解读与分析报告.pdf》</a>
        <a href="https://other.com/about.html">关于我们</a>
    </div>
</body>
</html>
"""

class TestCrawler(unittest.TestCase):
    def test_extract_article(self):
        crawler = PolicyCrawler()
        article = crawler.extract_article("https://example.sgcc.com.cn/policy/1001.html", SAMPLE_HTML)
        
        self.assertEqual(article["title"], "国家电网某项新规指导意见（试行）")
        self.assertEqual(article["publish_date"], "2024-05-18")
        self.assertIn("第一条 为了进一步规范电力市场交易秩序", article["content"])
        self.assertEqual(len(article["attachments"]), 2)
        
        att_urls = [a["url"] for a in article["attachments"]]
        self.assertIn("https://example.sgcc.com.cn/files/20240518_guideline.docx", att_urls)
        self.assertIn("https://example.sgcc.com.cn/files/20240518_summary.pdf", att_urls)

    def test_storage(self):
        storage = PolicyStorage()
        sample_data = [{"title": "测试政策", "url": "https://test.com", "content": "内容"}]
        json_path = storage.save_json(sample_data, "test_output.json")
        self.assertTrue(json_path.exists())
        json_path.unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()
