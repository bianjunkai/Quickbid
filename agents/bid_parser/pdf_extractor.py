"""
文件文本提取 — PDF + DOCX 双格式支持。

PDF：双引擎（pdfplumber / PyMuPDF），输出带 [PAGE: N] 标记
DOCX：python-docx 提取，输出带 [PARA: N] / [TABLE: N] 标记

用法：
    from agents.bid_parser.pdf_extractor import extract_file_text
    text = extract_file_text("tender.pdf")   # 自动识别 PDF
    text = extract_file_text("tender.docx")  # 自动识别 DOCX
"""

import os
import sys
from typing import Optional


def extract_text_pdfplumber(pdf_path: str) -> list[dict]:
    """
    使用 pdfplumber 提取 PDF 文本。

    Returns:
        [{page: int, text: str}, ...]
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber 未安装。请运行: uv pip install pdfplumber"
        )

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if text:
                pages.append({"page": i, "text": text})
            else:
                pages.append({"page": i, "text": ""})
    return pages


def extract_text_pymupdf(pdf_path: str) -> list[dict]:
    """
    使用 PyMuPDF (fitz) 提取 PDF 文本（备选引擎）。

    Returns:
        [{page: int, text: str}, ...]
    """
    try:
        import fitz
    except ImportError:
        raise ImportError(
            "PyMuPDF 未安装。请运行: uv pip install pymupdf"
        )

    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc, 1):
        text = page.get_text()
        pages.append({"page": i, "text": text})
    doc.close()
    return pages


def extract_text(
    pdf_path: str,
    engine: str = "pdfplumber",
    output_path: Optional[str] = None,
) -> str:
    """
    提取 PDF 文本，每页以 [PAGE: N] 标记。

    Args:
        pdf_path: PDF 文件路径
        engine: 引擎选择 — "pdfplumber"（默认）或 "pymupdf"
        output_path: 可选，将结果写入文件

    Returns:
        完整文本，每页以 [PAGE: N]\\n 开头

    Raises:
        FileNotFoundError: PDF 文件不存在
        ImportError: 引擎依赖未安装
    """
    import os

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    if engine == "pymupdf":
        pages = extract_text_pymupdf(pdf_path)
    else:
        pages = extract_text_pdfplumber(pdf_path)

    output_lines = []
    for p in pages:
        output_lines.append(f"\n[PAGE: {p['page']}]")
        output_lines.append(p["text"])

    full_text = "\n".join(output_lines)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_text)

    return full_text


# ============================================================
# 统一入口：自动识别 PDF / DOCX
# ============================================================

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",   # 旧版 .doc 尝试用 python-docx 处理（可能失败）
}

# 支持的 MIME 类型（用于无扩展名时的 magic byte 检测）
PDF_MAGIC = b"%PDF"
DOCX_MAGIC = b"PK\x03\x04"  # .docx 是 ZIP 格式（但 .doc 不是）


def detect_file_type(file_path: str) -> str:
    """
    自动检测文件类型。

    检测顺序：扩展名 → magic bytes

    Returns:
        "pdf" | "docx" | "unknown"
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SUPPORTED_EXTENSIONS:
        return SUPPORTED_EXTENSIONS[ext]

    # Magic byte 检测
    try:
        with open(file_path, "rb") as f:
            header = f.read(4)
        if header[:4] == PDF_MAGIC:
            return "pdf"
        if header[:4] == DOCX_MAGIC:
            return "docx"
    except Exception:
        pass

    return "unknown"


def extract_file_text(
    file_path: str,
    engine: str = "pdfplumber",
    output_path: Optional[str] = None,
) -> str:
    """
    统一文本提取入口 — 自动识别 PDF 或 DOCX。

    Args:
        file_path: 文件路径（.pdf 或 .docx）
        engine: PDF 引擎选择（仅 PDF 时生效）— "pdfplumber" / "pymupdf"
        output_path: 可选，将结果写入文件

    Returns:
        带位置标记的完整文本：
          PDF  → [PAGE: N] 标记
          DOCX → [PARA: N] / [TABLE: N] 标记

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的文件格式
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    file_type = detect_file_type(file_path)

    if file_type == "pdf":
        return extract_text(file_path, engine=engine, output_path=output_path)

    elif file_type == "docx":
        from agents.bid_parser.docx_extractor import extract_text_docx
        return extract_text_docx(file_path, output_path=output_path)

    else:
        raise ValueError(
            f"不支持的文件格式: {file_path}\n"
            f"支持的格式: {', '.join(SUPPORTED_EXTENSIONS.keys())}"
        )


def get_file_info(file_path: str) -> dict:
    """
    获取文件基本信息，用于 parser 自动模式选择。

    Returns:
        {
            type: "pdf" | "docx" | "unknown",
            size_bytes: int,
            estimated_pages: int,   # 估算页数
            engine: str,            # 推荐引擎
        }
    """
    if not os.path.exists(file_path):
        return {"type": "unknown", "size_bytes": 0, "estimated_pages": 0, "engine": ""}

    file_type = detect_file_type(file_path)
    size_bytes = os.path.getsize(file_path)

    if file_type == "pdf":
        # PDF：用文件大小估算页数
        estimated_pages = max(1, size_bytes // 35000)  # ~35KB/page

        # 尝试精确获取页数
        try:
            import fitz
            doc = fitz.open(file_path)
            estimated_pages = doc.page_count
            doc.close()
        except Exception:
            pass

        return {
            "type": "pdf",
            "size_bytes": size_bytes,
            "estimated_pages": estimated_pages,
            "engine": "pdfplumber",
        }

    elif file_type == "docx":
        # DOCX：用字符数估算
        try:
            from agents.bid_parser.docx_extractor import extract_docx_metadata
            meta = extract_docx_metadata(file_path)
            estimated_pages = meta.get("approx_pages", max(1, size_bytes // 50000))
        except Exception:
            estimated_pages = max(1, size_bytes // 50000)

        return {
            "type": "docx",
            "size_bytes": size_bytes,
            "estimated_pages": estimated_pages,
            "engine": "python-docx",
        }

    return {
        "type": "unknown",
        "size_bytes": size_bytes,
        "estimated_pages": 0,
        "engine": "",
    }
