"""
DOCX 文本提取 — 从 Word 文档中提取文本，保留结构标记。

Word 文档没有固定"页"的概念（分页取决于打印机/设置），
因此使用段落编号 [PARA: N] 和表格标记 [TABLE: N] 来定位。

用法：
    from agents.bid_parser.docx_extractor import extract_text_docx
    text = extract_text_docx("tender.docx")
"""

import re
from typing import Optional


def extract_text_docx(
    docx_path: str,
    output_path: Optional[str] = None,
) -> str:
    """
    从 .docx 文件中提取文本。

    输出格式：
        [PARA: 1] 段落文本...
        [TABLE: 1] | 列1 | 列2 | ...
        [PARA: 2] 段落文本...

    Args:
        docx_path: .docx 文件路径
        output_path: 可选，将结果写入文件

    Returns:
        带位置标记的完整文本
    """
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "python-docx 未安装。请运行: uv pip install python-docx"
        )

    import os
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"DOCX 文件不存在: {docx_path}")

    doc = Document(docx_path)
    output_lines = []
    para_idx = 0
    table_idx = 0

    # Word 文档中 paragraphs 和 tables 是交错的
    # python-docx 的 iter_inner_content 可以帮助我们按顺序遍历
    from docx.oxml.ns import qn

    body = doc.element.body

    for child in body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "p":
            # 段落
            para = _get_paragraph_text(child)
            if para.strip():
                para_idx += 1
                output_lines.append(f"\n[PARA: {para_idx}]")
                output_lines.append(para)

        elif tag == "tbl":
            # 表格
            table_idx += 1
            table_text = _get_table_text(child)
            if table_text.strip():
                output_lines.append(f"\n[TABLE: {table_idx}]")
                output_lines.append(table_text)

    full_text = "\n".join(output_lines)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_text)

    return full_text


def _get_paragraph_text(p_elem) -> str:
    """从 XML paragraph 元素提取文本，保留格式信息。"""
    from docx.oxml.ns import qn

    texts = []
    # 检查段落样式（标题等）
    style = p_elem.find(qn("w:pPr"))
    style_name = ""
    if style is not None:
        style_ref = style.find(qn("w:pStyle"))
        if style_ref is not None:
            style_name = style_ref.get(qn("w:val"), "")

    # 提取文本
    for run in p_elem.findall(qn("w:r")):
        # 检查加粗
        is_bold = False
        rpr = run.find(qn("w:rPr"))
        if rpr is not None:
            bold = rpr.find(qn("w:b"))
            if bold is not None:
                is_bold = True

        t_elem = run.find(qn("w:t"))
        if t_elem is not None and t_elem.text:
            text = t_elem.text
            if is_bold:
                text = f"**{text}**"
            texts.append(text)

    result = "".join(texts)

    # 标题加标记
    if style_name and "Heading" in style_name:
        level = style_name.replace("Heading", "").strip()
        if level.isdigit():
            prefix = "#" * min(int(level), 6)
            result = f"{prefix} {result}"

    return result


def _get_table_text(tbl_elem) -> str:
    """从 XML table 元素提取文本，转为 markdown 风格表格。"""
    from docx.oxml.ns import qn

    rows = []
    for tr in tbl_elem.findall(qn("w:tr")):
        cells = []
        for tc in tr.findall(qn("w:tc")):
            cell_texts = []
            for p in tc.findall(qn("w:p")):
                for run in p.findall(qn("w:r")):
                    t = run.find(qn("w:t"))
                    if t is not None and t.text:
                        cell_texts.append(t.text)
            cells.append("".join(cell_texts).replace("\n", " "))
        rows.append(" | " + " | ".join(cells) + " |")

    if rows:
        # 添加表头分隔线
        col_count = rows[0].count("|") - 1
        if col_count > 0 and len(rows) > 1:
            sep = " | " + " | ".join(["---"] * col_count) + " |"
            rows.insert(1, sep)

    return "\n".join(rows)


def extract_docx_metadata(docx_path: str) -> dict:
    """
    提取 .docx 文件的元数据。

    Returns:
        {
            paragraph_count: int,
            table_count: int,
            headings: [{level, text}, ...],
            approx_pages: int,  # 粗略估算
        }
    """
    try:
        from docx import Document
        from docx.oxml.ns import qn
    except ImportError:
        raise ImportError("python-docx 未安装")

    doc = Document(docx_path)
    body = doc.element.body

    para_count = 0
    table_count = 0
    headings = []
    total_chars = 0

    for child in body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "p":
            para = _get_paragraph_text(child)
            if para.strip():
                para_count += 1
                total_chars += len(para)
            # 检测标题
            style = child.find(qn("w:pPr"))
            if style is not None:
                style_ref = style.find(qn("w:pStyle"))
                if style_ref is not None:
                    name = style_ref.get(qn("w:val"), "")
                    if "Heading" in name:
                        level = name.replace("Heading", "").strip()
                        headings.append({
                            "level": int(level) if level.isdigit() else 0,
                            "text": para.strip()[:100],
                        })

        elif tag == "tbl":
            table_count += 1

    # 粗略估算页数：~2000字符/页
    approx_pages = max(1, total_chars // 2000)

    return {
        "paragraph_count": para_count,
        "table_count": table_count,
        "headings": headings,
        "total_chars": total_chars,
        "approx_pages": approx_pages,
    }
