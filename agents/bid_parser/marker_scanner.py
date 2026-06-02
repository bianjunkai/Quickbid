"""
标记符号正则扫描 — 定位所有特殊标记出现位置。

适配自 bid-parse skill 的 scripts/regex_scan.py

用法：
    from agents.bid_parser.marker_scanner import scan_markers, extract_pages
    pages = extract_pages(full_text)
    hits = scan_markers(pages, ["▲", "★", "●"])
    summary = summarize_markers(hits)
"""

import re
import json
from collections import Counter
from typing import Optional

from agents.bid_parser.schema import DEFAULT_MARKERS


def extract_pages(text: str) -> list[dict]:
    """
    将带位置标记的文本按页/段落分割。

    支持两种标记格式：
      PDF  → [PAGE: N]
      DOCX → [PARA: N] / [TABLE: N]

    统一返回 [{page: int, text: str}, ...]，
    其中 page 对于 DOCX 表示段落组的序号。

    Args:
        text: extract_file_text() 输出的文本

    Returns:
        [{page: int, text: str}, ...]
    """
    pages = []

    # 检测标记类型
    if "[PAGE:" in text:
        marker = "PAGE"
    elif "[PARA:" in text or "[TABLE:" in text:
        marker = "DOCX"
    else:
        # 无标记，整篇作为一个块
        return [{"page": 1, "text": text}]

    if marker == "PAGE":
        pattern = re.compile(r"\[PAGE:\s*(\d+)\]\n")
        parts = pattern.split(text)
        for i in range(1, len(parts), 2):
            page_num = int(parts[i])
            page_text = parts[i + 1] if i + 1 < len(parts) else ""
            pages.append({"page": page_num, "text": page_text})

    elif marker == "DOCX":
        # 对 DOCX，将每 50 个段落/表格编为一组（模拟"页"）
        pattern = re.compile(r"\[(PARA|TABLE):\s*(\d+)\]\n")
        parts = pattern.split(text)

        group_texts = []
        current_group = ""
        item_count = 0
        group_num = 0

        # parts 格式: [pre_text, type1, num1, text1, type2, num2, text2, ...]
        for i in range(1, len(parts), 3):
            if i + 2 < len(parts):
                item_text = parts[i + 2]
                current_group += item_text + "\n"
                item_count += 1

                if item_count >= 50:
                    group_num += 1
                    pages.append({"page": group_num, "text": current_group})
                    current_group = ""
                    item_count = 0

        if current_group.strip():
            group_num += 1
            pages.append({"page": group_num, "text": current_group})

    return pages


def scan_markers(
    pages: list[dict],
    markers: Optional[list[str]] = None,
) -> list[dict]:
    """
    扫描所有标记符号在文本中的出现位置。

    Args:
        pages: extract_pages() 返回的页面列表
        markers: 要扫描的标记符号列表，默认使用 DEFAULT_MARKERS

    Returns:
        命中列表，按页码和位置排序：
        [{symbol, page, position, line_text, context}, ...]
    """
    if markers is None:
        markers = DEFAULT_MARKERS

    results = []

    for p in pages:
        text = p["text"]
        if not text:
            continue

        for marker in markers:
            escaped = re.escape(marker)
            for m in re.finditer(escaped, text):
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 120)
                context = text[start:end].replace("\n", " ").strip()

                # 提取标记所在行
                line_start = text.rfind("\n", 0, m.start()) + 1
                line_end = text.find("\n", m.end())
                if line_end == -1:
                    line_end = len(text)
                line = text[line_start:line_end].strip()

                results.append(
                    {
                        "symbol": marker,
                        "page": p["page"],
                        "position": m.start(),
                        "line_text": line,
                        "context": context,
                    }
                )

    # 按页码和位置排序
    results.sort(key=lambda x: (x["page"], x["position"]))
    return results


def summarize_markers(hits: list[dict]) -> dict:
    """
    汇总标记扫描结果统计。

    Args:
        hits: scan_markers() 返回的命中列表

    Returns:
        {
            total_hits: int,
            page_count: int,
            by_symbol: {symbol: count, ...},
            by_page: {page: count, ...},
        }
    """
    if not hits:
        return {"total_hits": 0, "page_count": 0, "by_symbol": {}, "by_page": {}}

    by_symbol = Counter(h["symbol"] for h in hits)
    by_page = Counter(h["page"] for h in hits)
    pages = set(h["page"] for h in hits)

    return {
        "total_hits": len(hits),
        "page_count": len(pages),
        "by_symbol": dict(by_symbol),
        "by_page": dict(by_page),
    }


def export_hits_json(hits: list[dict], output_path: str) -> None:
    """将标记命中结果导出为 JSON 文件。"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(hits, f, ensure_ascii=False, indent=2)
