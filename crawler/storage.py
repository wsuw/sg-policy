import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List
import urllib.parse
from crawler.config import DOCS_DIR, METADATA_DIR

def sanitize_filename(filename: str, max_length: int = 120) -> str:
    """清理文件名中的非法字符"""
    # 移除非法字符
    clean = re.sub(r'[\\/*?:"<>|]', "", filename)
    clean = clean.strip()
    if not clean:
        clean = "untitled_doc"
    # 截断过长文件名
    return clean[:max_length]

class PolicyStorage:
    """政策数据存储处理器"""

    def __init__(self, output_dir: Path = METADATA_DIR, docs_dir: Path = DOCS_DIR):
        self.output_dir = Path(output_dir)
        self.docs_dir = Path(docs_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def save_json(self, data: List[Dict[str, Any]], filename: str = "policies.json") -> Path:
        """保存为 JSON 文件"""
        target_path = self.output_dir / filename
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return target_path

    def save_jsonl(self, data: List[Dict[str, Any]], filename: str = "policies.jsonl") -> Path:
        """保存为 JSONL 文件"""
        target_path = self.output_dir / filename
        with open(target_path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        return target_path

    def save_csv(self, data: List[Dict[str, Any]], filename: str = "policies.csv") -> Path:
        """保存为 CSV 文件"""
        if not data:
            return self.output_dir / filename

        target_path = self.output_dir / filename
        fieldnames = list(data[0].keys())
        with open(target_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        return target_path

    def save_document(self, content: bytes, original_filename: str) -> Path:
        """保存下载的文档附件（如 pdf, docx 等）"""
        clean_name = sanitize_filename(urllib.parse.unquote(original_filename))
        target_path = self.docs_dir / clean_name
        
        # 避免重名覆盖
        counter = 1
        stem = target_path.stem
        suffix = target_path.suffix
        while target_path.exists():
            target_path = self.docs_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        with open(target_path, "wb") as f:
            f.write(content)
        return target_path
