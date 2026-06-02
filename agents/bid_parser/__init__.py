"""
bid_parser — 招标文件智能解析子包

基于 bid-parse skill 的五步管道（支持 PDF + DOCX）：
  1. 文件文本提取（PDF: pdfplumber/PyMuPDF | DOCX: python-docx）
  2. 标记语义识别（LLM 识别 ▲★◇● 等符号的含义）
  3. 标记精准定位与抽取（正则扫描 + LLM 分批映射）
  4. 主体字段分段抽取（10 模块独立 LLM 调用）
  5. 合并与交叉校验

上游：Orchestrator 调度 ParserAgent
下游：MatcherAgent（材料匹配）、GeneratorAgent（标书生成）、ReviewerAgent（终审）
"""

from agents.bid_parser.schema import (
    BID_MODULE_DESCRIPTIONS,
    K01_K14_MAPPING,
    MARKER_PRIORITY,
    DEFAULT_MARKERS,
    SYMBOL_ALIASES,
)
from agents.bid_parser.pdf_extractor import (
    extract_text,
    extract_text_pdfplumber,
    extract_text_pymupdf,
    extract_file_text,
    detect_file_type,
    get_file_info,
)
from agents.bid_parser.docx_extractor import (
    extract_text_docx,
    extract_docx_metadata,
)
from agents.bid_parser.marker_scanner import (
    extract_pages,
    scan_markers,
    summarize_markers,
)
from agents.bid_parser.prompts import (
    MARKER_SEMANTICS_SYSTEM,
    MARKER_EXTRACTION_SYSTEM,
    EXTRACTION_PROMPTS,
    VALIDATION_SYSTEM,
    system_prompt_for_step,
    marker_semantics_messages,
    marker_extraction_messages,
    extraction_messages,
    validation_messages,
    quick_extraction_messages,
)
from agents.bid_parser.pipeline import (
    BidParsePipeline,
    BidLLMClient,
    full_result_to_k01_k14,
)

__all__ = [
    # Schema
    "BID_MODULE_DESCRIPTIONS",
    "K01_K14_MAPPING",
    "MARKER_PRIORITY",
    "DEFAULT_MARKERS",
    "SYMBOL_ALIASES",
    # File Extractors (PDF + DOCX)
    "extract_text",
    "extract_text_pdfplumber",
    "extract_text_pymupdf",
    "extract_file_text",
    "detect_file_type",
    "get_file_info",
    "extract_text_docx",
    "extract_docx_metadata",
    # Marker Scanner
    "extract_pages",
    "scan_markers",
    "summarize_markers",
    # Prompts
    "MARKER_SEMANTICS_SYSTEM",
    "MARKER_EXTRACTION_SYSTEM",
    "EXTRACTION_PROMPTS",
    "VALIDATION_SYSTEM",
    "system_prompt_for_step",
    "marker_semantics_messages",
    "marker_extraction_messages",
    "extraction_messages",
    "validation_messages",
    "quick_extraction_messages",
    # Pipeline
    "BidParsePipeline",
    "BidLLMClient",
    "full_result_to_k01_k14",
]
