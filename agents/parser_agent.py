"""
ParserAgent — 招标文件智能解析

基于 bid-parse skill 的五步管道：
  1. PDF 文本提取（双引擎：pdfplumber / PyMuPDF）
  2. 标记语义识别（LLM 识别 ▲★◇● 等符号含义）
  3. 标记精准定位与抽取（正则扫描 + LLM 分批映射）
  4. 主体字段分段抽取（10 模块独立 LLM 调用）
  5. 合并与交叉校验

输出同时包含完整结构化数据和 K01-K14 兼容格式。

模式：
  - full：完整五步管道（~10 次 LLM 调用）
  - quick：快速 K01-K14 提取（1 次 LLM 调用）
  - manual：无 LLM 可用时的降级模式（仅 PDF 提取 + 标记扫描）
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agents.base import BaseAgent, AgentContext
from agents.bid_parser.pipeline import (
    BidParsePipeline,
    BidLLMClient,
    full_result_to_k01_k14,
)
from agents.bid_parser.schema import (
    K01_K14_MAPPING,
    k_field_value,
    make_k_field,
)
from agents.bid_parser.pdf_extractor import extract_file_text, get_file_info
from agents.bid_parser.marker_scanner import extract_pages, scan_markers, summarize_markers


SYSTEM_PROMPT = """你是招标文件分析专家。你使用五步管道从招标文件 PDF 中提取结构化信息。

管道步骤：
1. PDF 文本提取 — 双引擎提取，保留所有 Unicode 符号
2. 标记语义识别 — LLM 识别 ▲★◇● 等符号的含义
3. 标记精准抽取 — 正则定位 + LLM 按优先级分批映射
4. 分段抽取 — 10 模块独立 LLM 调用
5. 合并校验 — 交叉验证 + 风险摘要

输出包含 11 个模块的完整结构化数据，以及向下兼容的 K01-K14 格式。"""


class ParserAgent(BaseAgent):
    """
    招标文件解析 Agent。

    execute() 支持三种模式：
    - auto（默认）：根据 PDF 大小和 LLM 可用性自动选择
    - full：完整五步管道
    - quick：快速 K01-K14 提取
    """

    name = "parser"
    description = "五步管道解析招标文件：文本提取 → 标记语义 → 标记抽取 → 分段抽取 → 合并校验"
    system_prompt = SYSTEM_PROMPT
    temperature = 0.0

    def __init__(self, config: dict | None = None):
        super().__init__()
        self.config = config or {}
        self._pipeline: Optional[BidParsePipeline] = None
        self._llm_client: Optional[BidLLMClient] = None

    # ================================================================
    # 主入口
    # ================================================================

    def execute(self, ctx: AgentContext) -> dict:
        """
        解析招标文件。

        优先从 ctx 中获取上下文信息，调用五步管道（或降级模式）。
        返回包含完整结构化数据 + K01-K14 兼容格式的 dict。

        Args:
            ctx: AgentContext，包含 project_id, tender 文件路径等

        Returns:
            {
                # K01-K14 兼容层
                "K01_项目名称": "...", ..., "K14_演示要求": "...",
                # 完整结构化数据
                "meta": {...}, "marker_semantics": {...}, "base": {...}, ...
            }
        """
        # 确定要解析的文件路径
        file_path = self._resolve_file_path(ctx)

        if not file_path:
            # 无文件路径 → 降级为从 ctx 已有数据构建
            return self._fallback_from_context(ctx)

        if not Path(file_path).exists():
            return self._error_result(f"招标文件不存在：{file_path}")

        # 决定执行模式：ctx 覆盖 > config.parser.mode > auto
        if getattr(ctx, "parser_mode_override", None) in {"auto", "quick", "full", "manual"}:
            mode = ctx.parser_mode_override
        else:
            mode = self.config.get("parser", {}).get("mode", "auto")
        if mode == "auto":
            mode = self._auto_select_mode(file_path)

        try:
            if mode == "quick":
                return self.execute_quick(ctx, file_path)
            elif mode == "full":
                return self.execute_full(ctx, file_path)
            else:
                # manual 模式
                return self.execute_manual(ctx, file_path)
        except Exception as e:
            return self._error_result(f"解析失败：{e}", exception=e)

    def execute_quick(self, ctx: AgentContext, file_path: str | None = None) -> dict:
        """
        快速模式：单次 LLM 调用提取 K01-K14。
        适用于需要快速反馈的场景。支持 PDF 和 DOCX。
        """
        if file_path is None:
            file_path = self._resolve_file_path(ctx)

        if not file_path or not Path(file_path).exists():
            return self._error_result("快速模式需要有效的招标文件路径")

        pipeline = self._get_pipeline()

        # 先用 pipeline 提文本，再快速提取
        full_text = pipeline.step1_extract_text(file_path)
        k01_k14 = pipeline.run_quick(file_path)

        if not k01_k14:
            # LLM 不可用，降级为 manual
            return self.execute_manual(ctx, file_path)

        # 补充缺失字段：新 shape 下空值/缺失都用 make_k_field 占位
        for i in range(1, 15):
            key = f"K{i:02d}"
            if key not in k01_k14 or k_field_value(k01_k14[key]) is None:
                k01_k14[key] = make_k_field("未找到", source_page=None)

        ctx.parsed_data = k01_k14
        ctx.error = None

        return {
            **k01_k14,
            "_mode": "quick",
            "_text_length": len(full_text),
        }

    def execute_full(self, ctx: AgentContext, file_path: str | None = None) -> dict:
        """
        完整模式（阶段 1）：单次 1M 上下文 LLM 解析，输出 K01-K14 + 8 模块 + 标记。

        1 次 LLM 调用替代旧的 ~10 次。耗时从 3-4 分钟降到 20-40 秒。
        支持 PDF 和 DOCX。
        """
        if file_path is None:
            file_path = self._resolve_file_path(ctx)

        if not file_path or not Path(file_path).exists():
            return self._error_result("完整模式需要有效的招标文件路径")

        pipeline = self._get_pipeline()

        # 运行新 3 步管道（阶段 1）
        full_result = pipeline.run(file_path)

        # 填充 meta（如果 LLM 没给）
        if not full_result.get("meta"):
            full_result["meta"] = self._build_meta(file_path)
        full_result["meta"].setdefault("parser_version", "3.1.0-full-context")
        full_result["meta"].setdefault("prompt_mode", "single-shot-1M-context")

        # 提取 K-层：新管道下 LLM 已直接给 K01-K14；只在缺失时用 formatter 从模块补
        k01_k14 = self._extract_k01_k14(full_result)

        # 合并输出（模块 + K-层 + meta）
        output = {
            **k01_k14,
            **{k: v for k, v in full_result.items() if k not in k01_k14},
            "_mode": full_result.get("_mode", "full"),
            "_text_length": full_result.get("meta", {}).get("text_length", 0),
        }

        ctx.parsed_data = output
        ctx.error = None

        return output

    def execute_manual(self, ctx: AgentContext, file_path: str | None = None) -> dict:
        """
        手动/降级模式：仅完成文件提取和标记扫描，不调用 LLM。

        返回基础文本信息和标记统计，等待用户手动补充或后续 LLM 处理。
        """
        if file_path is None:
            file_path = self._resolve_file_path(ctx)

        if not file_path or not Path(file_path).exists():
            return self._error_result("招标文件不存在")

        # 提取文本
        full_text = extract_file_text(file_path)

        # 扫描标记
        pages = extract_pages(full_text)
        hits = scan_markers(pages)
        summary = summarize_markers(hits)

        # 构建基础结果（K01-K14 全为"待提取"，用新 shape 占位）
        k01_k14 = {}
        for i in range(1, 15):
            key = f"K{i:02d}"
            if i == 1 and ctx.parsed_data:
                # K01 可能从项目名获取（兼容旧 shape 与新 shape）
                project_name = k_field_value(ctx.parsed_data.get("K01_项目名称"))
                k01_k14[key] = (
                    make_k_field(project_name, source_page=None)
                    if project_name
                    else make_k_field("待提取", source_page=None)
                )
            else:
                k01_k14[key] = make_k_field("待提取", source_page=None)

        output = {
            **k01_k14,
            "meta": self._build_meta(file_path, full_text),
            "marker_extractions": {
                "extraction_summary": {
                    "total_marker_occurrences": summary["total_hits"],
                    "total_mapped": 0,
                    "unmapped_count": summary["total_hits"],
                    "by_symbol": summary["by_symbol"],
                },
                "fatal_items": [],
                "critical_items": [],
                "high_items": [],
                "medium_items": [],
                "low_items": [],
            },
            "_mode": "manual",
            "_text_preview": full_text[:2000],
            "_text_length": len(full_text),
            "_marker_summary": summary,
            "_hint": "LLM 不可用或手动模式。请配置 TENDER_DEEPSEEK_API_KEY 环境变量以启用智能解析，或手动补充 K01-K14 字段。",
        }

        ctx.parsed_data = output
        ctx.error = None

        return output

    # ================================================================
    # 校验
    # ================================================================

    def validate_output(self, output: dict) -> bool:
        """验证输出包含必要的 K01-K14 字段（以 K01~K14 开头）。"""
        for i in range(1, 15):
            key_template = f"K{i:02d}"
            found = any(k.startswith(key_template) for k in output)
            if not found:
                return False
        return True

    # ================================================================
    # 辅助方法
    # ================================================================

    def _get_pipeline(self) -> BidParsePipeline:
        """懒初始化管道。"""
        if self._pipeline is None:
            ai_config = self.config.get("ai", {})
            self._llm_client = BidLLMClient(
                model=ai_config.get("model", "deepseek-v4-flash"),
                base_url=ai_config.get("base_url", "https://api.deepseek.com"),
            )
            parser_config = self.config.get("parser", {})
            self._pipeline = BidParsePipeline(self._llm_client, parser_config)
        return self._pipeline

    def _extract_k01_k14(self, full_result: dict) -> dict:
        """
        提取 K01-K14：优先用 LLM 直接给的 K-层（阶段 1 新管道）。
        LLM 已经在 FULL_PARSE_SYSTEM prompt 下输出 K01_项目名称/K04_预算金额 等字段。
        K 字段新 shape：标量 {value, source_page}、数组 {items, source_pages}。
        """
        k = {}
        for i in range(1, 15):
            key = f"K{i:02d}"
            # 找 K-层字段（key 形如 K01_项目名称 / K10_星标项 / K14_演示要求）
            for fk in full_result:
                if fk.startswith(f"{key}_") and k_field_value(full_result[fk]) is not None:
                    k[fk] = full_result[fk]
                    break
            else:
                continue
            # 找到了就不再 fallback（LLM 优先）
        return k

    def _resolve_file_path(self, ctx: AgentContext) -> Optional[str]:
        """
        从 AgentContext 解析招标文件路径（支持 PDF 和 DOCX）。

        优先级：
        1. ctx.parsed_data 中的 tender_file_path
        2. ctx.parsed_data 中的 file_path
        3. 通过 project_id 从 DB 查询
        """
        # 从 ctx 中查找
        path = ctx.parsed_data.get("tender_file_path") if ctx.parsed_data else None
        if not path and ctx.parsed_data:
            path = ctx.parsed_data.get("file_path")
        if path:
            return path

        # 从 DB 查询
        if ctx.project_id:
            try:
                from models import get_session, Project
                session = get_session()
                project = session.get(Project, ctx.project_id)
                if project and project.tender_file_path:
                    return project.tender_file_path
            except Exception:
                pass

        return None

    def _auto_select_mode(self, file_path: str) -> str:
        """
        根据条件自动选择模式（PDF 和 DOCX 通用）：
        - LLM 不可用 → manual
        - 文件 < 50 页 → quick
        - 文件 ≥ 50 页 → full
        """
        # 检查 LLM
        client = BidLLMClient()
        if not client.is_available:
            return "manual"

        # 用 get_file_info 获取准确页数估算
        try:
            info = get_file_info(file_path)
            estimated_pages = info.get("estimated_pages", 0)
            if estimated_pages > 0:
                return "full" if estimated_pages >= 50 else "quick"
        except Exception:
            pass

        # 回退：用文件大小粗略估算
        try:
            size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            estimated_pages = size_mb * 30
            return "full" if estimated_pages >= 50 else "quick"
        except Exception:
            return "quick"

    def _fallback_from_context(self, ctx: AgentContext) -> dict:
        """
        无 PDF 路径时的降级处理：返回 ctx 中已有的 parsed_data，
        或返回 mock 数据（保持与旧版兼容）。
        """
        if ctx.parsed_data and k_field_value(ctx.parsed_data.get("K01_项目名称")):
            ctx.error = None
            return {**ctx.parsed_data, "_mode": "context_reuse"}

        # 完全降级 — 返回基础结构（K 字段全部用新 shape 占位）
        existing = ctx.parsed_data or {}
        project_name_value = k_field_value(existing.get("K01_项目名称"))
        return {
            "K01_项目名称": (
                make_k_field(project_name_value, source_page=None)
                if project_name_value
                else make_k_field("待提取", source_page=None)
            ),
            "K02_招标编号": make_k_field("待提取", source_page=None),
            "K03_招标人": make_k_field("待提取", source_page=None),
            "K04_预算金额": make_k_field("待提取", source_page=None),
            "K05_投标截止时间": make_k_field("待提取", source_page=None),
            "K06_开标时间": make_k_field("待提取", source_page=None),
            "K07_评分标准": make_k_field("待提取", source_page=None),
            "K08_技术要求": make_k_field("待提取", source_page=None),
            "K09_商务资质要求": make_k_field("待提取", source_page=None),
            "K10_星标项": make_k_field([], source_page=None),
            "K11_废标条款": make_k_field([], source_page=None),
            "K12_章节模板要求": make_k_field("待提取", source_page=None),
            "K13_偏离表格式要求": make_k_field("待提取", source_page=None),
            "K14_演示要求": make_k_field("待提取", source_page=None),
            "_mode": "fallback",
            "_hint": "未找到 PDF 文件路径。请先创建项目并上传招标文件。",
        }

    def _build_meta(self, file_path: str, full_text: str | None = None) -> dict:
        """构建 meta 信息（PDF 和 DOCX 通用）。"""
        file_obj = Path(file_path)
        page_count = 0
        if full_text:
            import re
            # PDF 页面计数
            pages = re.findall(r"\[PAGE:\s*(\d+)\]", full_text)
            if pages:
                page_count = len(pages)
            else:
                # DOCX 段落计数
                paras = re.findall(r"\[PARA:\s*(\d+)\]", full_text)
                if paras:
                    page_count = max(1, len(paras) // 50)  # ~50段/页

        return {
            "parse_id": str(uuid.uuid4()),
            "source_file": file_obj.name,
            "parse_time": datetime.now(timezone.utc).isoformat(),
            "parser_version": "3.0.0",
            "page_count": page_count,
            "warnings": [],
        }

    def _error_result(self, message: str, exception: Exception | None = None) -> dict:
        """构建错误结果。"""
        ctx_error = message
        if exception:
            ctx_error = f"{message} ({type(exception).__name__}: {exception})"

        return {
            "K01_项目名称": make_k_field("解析失败", source_page=None),
            "K02_招标编号": make_k_field("解析失败", source_page=None),
            "K03_招标人": make_k_field("解析失败", source_page=None),
            "K04_预算金额": make_k_field("解析失败", source_page=None),
            "K05_投标截止时间": make_k_field("解析失败", source_page=None),
            "K06_开标时间": make_k_field("解析失败", source_page=None),
            "K07_评分标准": make_k_field("解析失败", source_page=None),
            "K08_技术要求": make_k_field("解析失败", source_page=None),
            "K09_商务资质要求": make_k_field("解析失败", source_page=None),
            "K10_星标项": make_k_field([], source_page=None),
            "K11_废标条款": make_k_field([], source_page=None),
            "K12_章节模板要求": make_k_field("解析失败", source_page=None),
            "K13_偏离表格式要求": make_k_field("解析失败", source_page=None),
            "K14_演示要求": make_k_field("解析失败", source_page=None),
            "_mode": "error",
            "_error": message,
        }
