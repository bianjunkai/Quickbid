"""
BidParsePipeline — 五步解析管道 + LLM 客户端

支持 PDF 和 DOCX 招标文件。

管道路径：
  Step 1: 文件文本提取（PDF/DOCX，本地，不需 LLM）
  Step 2: 标记语义识别（1 次 LLM）
  Step 3: 标记精准抽取（正则扫描 + 分批 LLM）
  Step 4: 主体字段分段抽取（10 模块，保守 6 次 LLM）
  Step 5: 合并与交叉校验（0~1 次 LLM）

LLM 调用策略：每次调用聚焦单个任务，temperature=0.0。
"""

import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from agents.bid_parser.schema import (
    DEFAULT_MARKERS,
    K01_K14_MAPPING,
    K01_K14_FORMATTERS,
    _format_scoring,
    _format_tech,
    _format_qualification,
    _format_marker_items,
    _format_rejection,
    _format_templates,
    _format_deviation,
    _format_presentation,
    make_k_field,
)
from agents.bid_parser.pdf_extractor import (
    extract_file_text,
    get_file_info,
)
from agents.bid_parser.marker_scanner import (
    extract_pages,
    scan_markers,
    summarize_markers,
)
from agents.bid_parser.prompts import (
    marker_semantics_messages,
    marker_extraction_messages,
    extraction_messages,
    validation_messages,
    quick_extraction_messages,
    full_parse_messages,
)


# ============================================================
# LLM Client
# ============================================================

class BidLLMClient:
    """
    DeepSeek API 轻量封装（OpenAI 兼容接口）。

    用法：
        client = BidLLMClient()
        result = client.chat(messages, temperature=0.0)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
    ):
        self.api_key = api_key or os.environ.get("TENDER_DEEPSEEK_API_KEY", "")
        self.base_url = base_url
        self.model = model
        self._client = None

    @property
    def is_available(self) -> bool:
        """LLM 客户端是否可用。"""
        return bool(self.api_key)

    def _get_client(self):
        """懒初始化 OpenAI 客户端。"""
        if self._client is None and self.is_available:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                )
            except ImportError:
                raise ImportError(
                    "openai SDK 未安装。请运行: uv pip install openai"
                )
        return self._client

    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        """
        调用 LLM 聊天（非流式）。

        Args:
            messages: OpenAI 格式的消息列表
            temperature: 采样温度
            max_tokens: 最大输出 token 数
            response_format: 响应格式（如 {"type": "json_object"}）

        Returns:
            LLM 响应文本，如果不可用返回 None
        """
        if not self.is_available:
            return None

        client = self._get_client()
        if client is None:
            return None

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def chat_stream(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 16384,
        response_format: Optional[dict] = None,
    ) -> Iterator[str]:
        """
        流式调用 LLM，逐 token 产出（生成器）。

        用法：
            for token in client.chat_stream(messages):
                print(token, end="", flush=True)

        Args:
            同 chat()

        Yields:
            LLM 响应的文本片段
        """
        if not self.is_available:
            return

        client = self._get_client()
        if client is None:
            return

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            t0 = time.time()
            chunk_count = 0
            stream = client.chat.completions.create(**kwargs)
            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    chunk_count += 1
                    # 诊断日志：前 3 个 chunk + 每 100 个打一个
                    if chunk_count <= 3 or chunk_count % 100 == 0:
                        logging.getLogger(__name__).info(
                            "[stream] #%d +%.2fs len=%d: %r",
                            chunk_count, time.time() - t0, len(content), content[:60],
                        )
                    yield content
            logging.getLogger(__name__).info(
                "[stream] done: total %d chunks in %.2fs",
                chunk_count, time.time() - t0,
            )
        except Exception as e:
            # 流式失败：把错误作为最后一段文本抛出
            logging.getLogger(__name__).error("[stream] error: %s", e)
            yield f"\n\n[STREAM_ERROR] {type(e).__name__}: {e}"

    def chat_json(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> Optional[dict]:
        """
        调用 LLM 并解析 JSON 响应。

        Returns:
            解析后的 dict，失败返回 None
        """
        text = self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        if text is None:
            return None

        # 尝试提取 JSON（处理 markdown 代码块包裹的情况）
        text = text.strip()
        if text.startswith("```"):
            # 移除 markdown 代码块标记
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试修复常见问题
            return None

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        tool_choice: str | dict = "auto",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> Optional[dict]:
        """
        调用 LLM 并支持 tool-use（OpenAI 兼容协议）。

        Args:
            messages: OpenAI 格式消息列表（支持 assistant 消息携带 tool_calls、
                       以及 role="tool" 的工具执行结果消息）
            tools: OpenAI 风格的 tools 列表，每项形如：
                   {"type": "function", "function": {"name": ..., "description": ...,
                    "parameters": <JSON Schema dict>}}
            tool_choice: "auto" / "none" / {"type": "function", "function": {"name": ...}}
            temperature: 采样温度
            max_tokens: 最大输出 token 数

        Returns:
            {
              "content": str | None,
              "tool_calls": [
                {"id": str, "name": str, "arguments": dict}, ...
              ] | None,
              "finish_reason": str,
            }
            若 LLM 不可用返回 None
        """
        if not self.is_available:
            return None

        client = self._get_client()
        if client is None:
            return None

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            return {"error": f"{type(e).__name__}: {e}", "content": None, "tool_calls": None}

        msg = response.choices[0].message
        tool_calls = None
        if msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except (json.JSONDecodeError, AttributeError):
                    args = {}
                tool_calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": args,
                    }
                )
        return {
            "content": msg.content,
            "tool_calls": tool_calls,
            "finish_reason": response.choices[0].finish_reason,
        }


# ============================================================
# 五步管道
# ============================================================

class BidParsePipeline:
    """
    招标文件解析五步管道。

    用法：
        client = BidLLMClient()
        pipeline = BidParsePipeline(client)
        result = pipeline.run("tender.pdf")

    或逐步骤：
        text = pipeline.step1_extract_text("tender.pdf")
        markers = pipeline.step2_detect_markers(text)
        extractions = pipeline.step3_scan_and_extract(text, markers)
        fields = pipeline.step4_extract_fields(text, extractions)
        final = pipeline.step5_merge_and_validate([markers, extractions, fields])
    """

    def __init__(self, llm_client: BidLLMClient, config: dict | None = None):
        self.llm = llm_client
        self.config = config or {}
        self.pdf_engine = self.config.get("pdf_engine", "pdfplumber")
        self.marker_scan_enabled = self.config.get("marker_scan", {}).get("enabled", True)
        self.llm_batch_size = self.config.get("llm_batch_size", 50)

    # ================================================================
    # Step 1: 文件文本提取（PDF / DOCX）
    # ================================================================

    def step1_extract_text(self, file_path: str) -> str:
        """
        文件 → 带位置标记的纯文本。

        支持格式：
          PDF  → [PAGE: N] 标记
          DOCX → [PARA: N] / [TABLE: N] 标记

        Returns:
            带位置标记的完整文本
        """
        return extract_file_text(file_path, engine=self.pdf_engine)

    # ============================================================
    # Step 2: 单次全量 LLM 解析（阶段 1：替代旧的 step2-4）
    # ============================================================

    def step2_full_parse(self, full_text: str) -> dict:
        """
        单次 LLM 调用解析全文，输出 14 K + 8 模块 + 标记抽取的完整 JSON。

        依赖：DeepSeek V3.1+ / V4 1M 上下文。
        79 页 PDF ≈ 25K tokens 输入，1 次调用同时拿到：
          - K01-K14 用户友好层（字符串/数组）
          - 8 个结构化模块
          - marker_extractions 5 个优先级数组
        """
        if not self.llm.is_available:
            return {
                "_error": "LLM 不可用，请配置 TENDER_DEEPSEEK_API_KEY",
                "_mode": "manual",
            }

        messages = full_parse_messages(full_text)
        # 16K 输出足够装下 14 K + 8 模块 + 67 标记条目
        result = self.llm.chat_json(messages, temperature=0.0, max_tokens=16384)

        if not result:
            # 一次失败重试一次（用稍高温度避免相同截断）
            result = self.llm.chat_json(messages, temperature=0.1, max_tokens=16384)

        if not result:
            return {
                "_error": "LLM 解析失败（连续 2 次调用均无响应）",
                "_mode": "error",
            }

        # 注入 meta 信息
        result.setdefault("meta", {})
        result["meta"]["parser_version"] = "3.1.0-full-context"
        result["meta"]["text_length"] = len(full_text)
        result["meta"]["prompt_mode"] = "single-shot-1M-context"

        return result

    def step2_full_parse_stream(self, full_text: str) -> Iterator[str]:
        """
        流式版本的 step2_full_parse：逐 token 产出 LLM 响应文本。

        适用于 SSE 端点 — 前端可看到 LLM 真正在生成 token，
        而非面对 65 秒黑屏。

        注意：streaming 调用**不传 response_format**。DeepSeek / OpenAI 兼容 API 在
        streaming + json_object 组合下会等完整响应生成完才返回 chunk（不是真正的
        逐 token 流），前端 SSE 看着就像"黑屏 N 秒 + 一次全有"。我们的 system
        prompt 已经强制要求 JSON 输出（且 JSON 会被 markdown fence 包起来），
        流完后由调用方剥 fence + json.loads 兜底，错误情况下返回 None。

        Yields:
            LLM 输出的 JSON 文本片段（不解析，留给调用方处理）
        """
        if not self.llm.is_available:
            yield "[LLM_UNAVAILABLE]"
            return

        messages = full_parse_messages(full_text)
        for tok in self.llm.chat_stream(
            messages, temperature=0.0, max_tokens=16384,
        ):
            yield tok

    def collect_stream_to_dict(
        self, stream: Iterator[str], text_length: int
    ) -> Optional[dict]:
        """
        把 step2_full_parse_stream 的输出聚合成完整 JSON dict。

        用途：SSE 端点一边 yield token 给前端，一边后台聚合。
        前端拿到完整 token 流时，后端立即解析为 dict 落库。
        """
        chunks: list[str] = []
        for tok in stream:
            chunks.append(tok)
        text = "".join(chunks)
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
        if not text or text == "[LLM_UNAVAILABLE]":
            return None
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            return None
        # 注入 meta
        result.setdefault("meta", {})
        result["meta"]["parser_version"] = "3.1.0-full-context"
        result["meta"]["text_length"] = text_length
        result["meta"]["prompt_mode"] = "single-shot-1M-context"
        return result

    # ============================================================
    # Step 3: 本地校验与合并（无 LLM）
    # ============================================================

    def step3_validate(self, parsed: dict, full_text: str) -> dict:
        """
        本地校验：模块完整性 + K-层/模块-层一致性 + 必填字段。

        Returns:
            在 parsed 基础上添加 _validation 和补全的最终 dict
        """
        final = dict(parsed)  # 浅拷贝
        self._augment_low_price_review(final, full_text)
        local_issues = self._local_validation(final)
        # 文本长度（即使 LLM 没填也保证前端能拿到）
        final.setdefault("meta", {})
        final["meta"].setdefault("text_length", len(full_text))
        final["_validation"] = {
            "method": "local",
            "issues": local_issues,
        }
        return final

    def _augment_low_price_review(self, final: dict, full_text: str):
        """Ensure low/abnormally-low bid review clauses are preserved."""
        clauses = self._find_low_price_review_clauses(full_text)
        if not clauses:
            return

        first = clauses[0]
        summary = "；".join(c["text"] for c in clauses[:3])
        scoring = final.get("scoring")
        if not isinstance(scoring, dict):
            scoring = {}
            final["scoring"] = scoring
        low_price = scoring.get("low_price_review")
        if not isinstance(low_price, dict):
            low_price = {}
            scoring["low_price_review"] = low_price
        low_price.setdefault("trigger", first["text"])
        low_price.setdefault("consequence", self._infer_low_price_consequence(summary))
        low_price.setdefault("source_page", first["page"])

        self._append_k_field_text(
            final,
            "K07_评分标准",
            f"低价审核风险：{summary}",
            first["page"],
        )
        self._append_k_array_item(
            final,
            "K10_星标项",
            f"低价审核风险：{summary}",
            first["page"],
        )

        marker_extractions = final.get("marker_extractions")
        if not isinstance(marker_extractions, dict):
            marker_extractions = {}
            final["marker_extractions"] = marker_extractions
        high_items = marker_extractions.get("high_items")
        if not isinstance(high_items, list):
            high_items = []
            marker_extractions["high_items"] = high_items
        exists = any(
            "低价" in str(item.get("raw_text", ""))
            for item in high_items
            if isinstance(item, dict)
        )
        if not exists:
            high_items.append({
                "marker": "低价审核",
                "source_page": first["page"],
                "raw_text": summary,
                "semantic": "报价阶段必须避免触发低价或异常低价审核",
            })

    @staticmethod
    def _find_low_price_review_clauses(full_text: str) -> list[dict[str, Any]]:
        keywords = [
            "低价审核",
            "异常低价",
            "低于成本",
            "明显低于其他投标",
            "报价明显低",
            "价格评审异常",
            "低价风险",
        ]
        clauses: list[dict[str, Any]] = []
        for page in extract_pages(full_text):
            page_no = page.get("page")
            text = page.get("text") or ""
            for line in re.split(r"[\n。；;]", text):
                line = re.sub(r"\s+", " ", line).strip()
                if not line:
                    continue
                if any(kw in line for kw in keywords):
                    clauses.append({
                        "page": page_no if isinstance(page_no, int) else None,
                        "text": line[:300],
                    })
                    break
        return clauses[:5]

    @staticmethod
    def _infer_low_price_consequence(text: str) -> str:
        if any(kw in text for kw in ["废标", "否决", "无效投标", "不推荐", "不作为中标"]):
            return "可能导致否决、废标或不推荐中标"
        if any(kw in text for kw in ["澄清", "说明", "证明"]):
            return "可能要求投标人澄清、说明或提交证明材料"
        return "报价阶段需避免触发低价或异常低价审核"

    @staticmethod
    def _append_k_field_text(final: dict, key: str, text: str, page: int | None):
        field = final.get(key)
        if isinstance(field, dict) and "value" in field:
            value = str(field.get("value") or "")
            if "低价" not in value and "异常低价" not in value:
                field["value"] = f"{value}；{text}" if value and value != "未找到" else text
            field.setdefault("source_page", page)
            return
        if not field or field == "未找到":
            final[key] = make_k_field(text, source_page=page)

    @staticmethod
    def _append_k_array_item(final: dict, key: str, text: str, page: int | None):
        field = final.get(key)
        if isinstance(field, dict) and "items" in field:
            items = field.get("items")
            if not isinstance(items, list):
                items = []
                field["items"] = items
            pages = field.get("source_pages")
            if not isinstance(pages, list):
                pages = []
                field["source_pages"] = pages
            if not any("低价" in str(item) for item in items):
                items.append(text)
                pages.append(page)
            return
        if isinstance(field, list):
            if not any("低价" in str(item) for item in field):
                field.append(text)
            return
        final[key] = {"items": [text], "source_pages": [page]}

    # ================================================================
    # Step 2: 标记语义识别
    # ================================================================

    def step2_detect_markers(self, full_text: str) -> dict:
        """
        LLM 通读全文，识别所有特殊标记符号并理解语义。

        Returns:
            marker_semantics JSON，包含 detection.markers[]
            如果 LLM 不可用，返回空结构
        """
        if not self.llm.is_available:
            return {
                "detection": {
                    "total_marker_types_found": 0,
                    "markers": [],
                    "_note": "LLM 不可用，跳过标记语义识别",
                }
            }

        messages = marker_semantics_messages(full_text)
        result = self.llm.chat_json(messages, temperature=0.0)

        if result is None:
            return {
                "detection": {
                    "total_marker_types_found": 0,
                    "markers": [],
                    "_note": "LLM 调用失败",
                }
            }

        return result

    # ================================================================
    # Step 3: 标记精准定位与抽取
    # ================================================================

    def step3_scan_and_extract(
        self,
        full_text: str,
        marker_semantics: dict,
    ) -> dict:
        """
        正则扫描全文 + 按优先级分批 LLM 抽取。

        流程：
        1. 正则扫描所有标记出现位置
        2. 按优先级分组（FATAL+CRITICAL / HIGH / MEDIUM+LOW）
        3. 每批送 LLM 抽取结构化内容

        Returns:
            marker_extractions JSON
        """
        # 3a. 正则扫描
        pages = extract_pages(full_text)
        hits = scan_markers(pages)
        summary = summarize_markers(hits)

        # 获取语义信息
        markers_info = marker_semantics.get("detection", {}).get("markers", [])

        # 按优先级分组标记
        priority_groups = {"FATAL": [], "CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}

        for hit in hits:
            symbol = hit["symbol"]
            # 查找该符号的语义信息
            sem_info = None
            for m in markers_info:
                if m.get("symbol") == symbol:
                    sem_info = m
                    break

            priority = sem_info.get("priority", "MEDIUM") if sem_info else "MEDIUM"
            if priority in priority_groups:
                priority_groups[priority].append(hit)
            else:
                priority_groups["MEDIUM"].append(hit)

        # 3b. 按优先级分批 LLM 抽取
        all_items = {
            "extraction_summary": {
                "total_marker_occurrences": summary["total_hits"],
                "total_mapped": 0,
                "unmapped_count": summary["total_hits"],
                "unmapped_detail": [],
            },
            "fatal_items": [],
            "critical_items": [],
            "high_items": [],
            "medium_items": [],
            "low_items": [],
        }

        if not self.llm.is_available:
            all_items["extraction_summary"]["_note"] = "LLM 不可用，仅完成正则扫描"
            # 原始命中作为 unmapped_detail
            for h in hits:
                all_items["extraction_summary"]["unmapped_detail"].append({
                    "symbol": h["symbol"],
                    "page": h["page"],
                    "raw_text_snippet": h["line_text"][:200],
                    "failure_reason": "LLM 不可用",
                })
            return all_items

        # 分批调用 LLM（每批最多 llm_batch_size 条）
        batch_configs = [
            ("FATAL", "fatal_items"),
            ("CRITICAL", "critical_items"),
            ("HIGH", "high_items"),
            ("MEDIUM", "medium_items"),
            ("LOW", "low_items"),
        ]

        total_mapped = 0

        for priority, output_key in batch_configs:
            group = priority_groups.get(priority, [])
            if not group:
                continue

            # 分批（避免单次调用太长）
            for batch_start in range(0, len(group), self.llm_batch_size):
                batch = group[batch_start : batch_start + self.llm_batch_size]

                # 获取该批标记的语义信息
                first_sym = batch[0]["symbol"]
                sem_label = priority
                target_field = ""
                for m in markers_info:
                    if m.get("symbol") == first_sym:
                        sem_label = m.get("semantic_label", priority)
                        target_field = m.get("maps_to_field", "")
                        break

                messages = marker_extraction_messages(
                    marker_symbol=first_sym,
                    semantic_label=sem_label,
                    priority=priority,
                    target_field=target_field,
                    hits=batch,
                )

                result = self.llm.chat_json(messages, temperature=0.0)
                if result and isinstance(result, list):
                    all_items[output_key].extend(result)
                    total_mapped += len(result)

        # 更新统计
        all_items["extraction_summary"]["total_mapped"] = total_mapped
        all_items["extraction_summary"]["unmapped_count"] = (
            summary["total_hits"] - total_mapped
        )
        all_items["extraction_summary"]["by_symbol"] = summary["by_symbol"]

        return all_items

    # ================================================================
    # Step 4: 主体字段分段抽取
    # ================================================================

    def step4_extract_fields(
        self,
        full_text: str,
        marker_data: dict,
    ) -> dict:
        """
        按模块分段 LLM 抽取所有主体字段。

        调用计划（按依赖顺序）：
        1. base（基本信息）
        2. qualification（资格条件）
        3. rejection（否决条款）
        4. scoring（评分标准）
        5. tech（技术需求）— 合并 functional + non_functional + security
        6. commercial（商务需求）
        7. templates（模板要求）
        8. logistics（操作要求）

        Returns:
            包含所有模块的完整 dict
        """
        # 构建标记上下文（将 Step 3 结果序列化为文本）
        marker_context = self._build_marker_context(marker_data)

        # 模块列表：(module_key, label, 章节关键词)
        modules = [
            ("base", "基本信息", ["投标邀请", "投标人须知", "招标公告", "第一章", "第一节"]),
            ("qualification", "资格条件", ["资格", "资质", "投标人资格", "资格审查"]),
            ("rejection", "否决/废标条件", ["否决", "废标", "无效投标", "初审"]),
            ("scoring", "评分标准", ["评分", "评审", "评标", "打分"]),
            ("tech", "技术需求", ["技术", "功能", "需求", "系统", "软件", "硬件"]),
            ("commercial", "商务需求", ["商务", "合同", "付款", "质保", "违约"]),
            ("templates", "标书模板要求", ["投标文件", "格式", "装订", "封装", "签署"]),
            ("logistics", "操作要求", ["递交", "开标", "踏勘", "答疑", "演示"]),
        ]

        results = {}

        for module_key, label, keywords in modules:
            # 提取相关章节
            chapter_text = self._extract_relevant_chapters(full_text, keywords)

            if not chapter_text.strip():
                results[module_key] = {}
                continue

            # 构建 prompt
            messages = extraction_messages(
                module_key=module_key,
                chapter_text=chapter_text[:8000],  # 限制长度
                marker_context=marker_context,
            )

            # LLM 调用
            if self.llm.is_available:
                result = self.llm.chat_json(messages, temperature=0.0)
                if result:
                    results[module_key] = result
                else:
                    results[module_key] = {}
            else:
                results[module_key] = {}

        return results

    # ================================================================
    # Step 5: 合并与交叉校验
    # ================================================================

    def step5_merge_and_validate(
        self,
        marker_semantics: dict,
        marker_extractions: dict,
        field_results: dict,
    ) -> dict:
        """
        合并所有部分，执行交叉校验。

        Args:
            marker_semantics: Step 2 输出
            marker_extractions: Step 3 输出
            field_results: Step 4 输出（各模块 dict）

        Returns:
            完整的最终解析结果 dict
        """
        # 合并
        final = {
            "meta": field_results.get("meta", {}),
            "marker_semantics": marker_semantics,
            "marker_extractions": marker_extractions,
            "base": field_results.get("base", {}),
            "qualification": field_results.get("qualification", {}),
            "rejection": field_results.get("rejection", {}),
            "scoring": field_results.get("scoring", {}),
            "tech": field_results.get("tech", {}),
            "commercial": field_results.get("commercial", {}),
            "templates": field_results.get("templates", {}),
            "logistics": field_results.get("logistics", {}),
        }

        # 本地校验（不依赖 LLM）
        local_issues = self._local_validation(final)

        final["_validation"] = {
            "method": "local",
            "issues": local_issues,
        }

        return final

    # ================================================================
    # 主入口
    # ================================================================

    def run(self, file_path: str) -> dict:
        """
        执行新 3 步管道（阶段 1）：

          Step 1: 文件文本提取（本地）
          Step 2: 单次 LLM 全量解析（1M 上下文，1 次调用）
          Step 3: 本地校验与合并

        旧的 5 步管道方法（step2_detect_markers / step3_scan_and_extract /
        step4_extract_fields / step5_merge_and_validate）保留供向后兼容，
        但不再被 run() 调用。
        """
        # Step 1: 文件文本提取
        full_text = self.step1_extract_text(file_path)

        # Step 2: 单次 LLM 解析
        parsed = self.step2_full_parse(full_text)
        if parsed.get("_mode") in ("manual", "error"):
            # LLM 不可用或调用失败，保留错误信息直接返回（前端会展示）
            parsed.setdefault("meta", {})
            parsed["meta"]["text_length"] = len(full_text)
            return parsed

        # Step 3: 本地校验
        final = self.step3_validate(parsed, full_text)
        return final

    def run_quick(self, file_path: str) -> dict:
        """
        快速模式：仅提取文本 + 单次 LLM 调用提取 K01-K14。

        用于需要快速反馈的场景。支持 PDF 和 DOCX。
        """
        full_text = self.step1_extract_text(file_path)

        if not self.llm.is_available:
            return {}

        messages = quick_extraction_messages(full_text)
        result = self.llm.chat_json(messages, temperature=0.0)
        return result if result else {}

    # ================================================================
    # 辅助方法
    # ================================================================

    def _build_marker_context(self, marker_data: dict) -> str:
        """将标记抽取结果转为 LLM 可读的上下文文本。"""
        parts = []
        for priority_key in ["fatal_items", "critical_items", "high_items"]:
            items = marker_data.get(priority_key, [])
            if items:
                parts.append(f"\n### {priority_key}")
                for item in items:
                    parts.append(
                        f"- [{item.get('marker', '')}] p{item.get('source_page', '?')} "
                        f"{item.get('raw_text', '')[:150]}"
                    )
        return "\n".join(parts) if parts else ""

    def _extract_relevant_chapters(
        self, full_text: str, keywords: list[str]
    ) -> str:
        """
        从全文中提取与关键词相关的章节。

        简单实现：按页搜索，包含关键词的页面全部纳入。
        """
        pages = extract_pages(full_text)
        relevant_pages = []

        for p in pages:
            text_lower = p["text"].lower()
            for kw in keywords:
                if kw.lower() in text_lower:
                    relevant_pages.append(p)
                    break

        if not relevant_pages:
            # 如果没找到相关页面，返回前几页（基本信息通常在前面）
            return "\n\n".join(
                f"[PAGE: {p['page']}]\n{p['text']}" for p in pages[:10]
            )

        return "\n\n".join(
            f"[PAGE: {p['page']}]\n{p['text']}" for p in relevant_pages[:20]
        )

    def _local_validation(self, final: dict) -> list[dict]:
        """本地逻辑校验（不依赖 LLM）。"""
        issues = []

        # 校验 marker_extractions 映射完整性
        extractions = final.get("marker_extractions", {})
        summary = extractions.get("extraction_summary", {})
        unmapped = summary.get("unmapped_count", 0)
        if unmapped > 0:
            issues.append({
                "severity": "warning",
                "type": "unmapped_markers",
                "field": "marker_extractions",
                "description": f"有 {unmapped} 处标记未能映射到结构化字段",
            })

        # 校验必填模块
        required_modules = ["base", "qualification", "rejection", "scoring", "tech", "commercial", "templates", "logistics"]
        for module in required_modules:
            if not final.get(module):
                issues.append({
                    "severity": "warning",
                    "type": "missing_module",
                    "field": module,
                    "description": f"{module} 模块为空",
                })

        # 校验 base 必填字段
        base = final.get("base", {})
        if isinstance(base, dict):
            base_required = ["project_name", "project_no", "bid_opening", "budget"]
            for field in base_required:
                if not base.get(field):
                    issues.append({
                        "severity": "warning",
                        "type": "missing_field",
                        "field": f"base.{field}",
                        "description": f"base.{field} 未提取到",
                    })

        return issues


# ============================================================
# K01-K14 格式转换
# ============================================================

def full_result_to_k01_k14(full_result: dict) -> dict:
    """
    将完整解析结果映射为 K01-K14 兼容格式。

    供 ParserAgent 在 execute() 返回时使用，保持与 Orchestrator 的向后兼容。

    注意：fallback 路径下 8 个结构化模块本身不带 source_page，所以这里产出的 K 字段
    page 为 null。K 层带 source_page 的来源是 LLM 在 FULL_PARSE_SYSTEM / QUICK_EXTRACTION_SYSTEM
    prompt 下直接返回的 K 字段，那是更优路径。
    """
    k01_k14 = {}

    # 辅助：从嵌套 dict 中按路径取值
    def _get_nested(data: dict, path: str):
        keys = path.split(".")
        val = data
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return None
            if val is None:
                return None
        return val

    for key, mapping in K01_K14_MAPPING.items():
        source = mapping["source"]
        value = _get_nested(full_result, source)

        # 尝试 fallback
        if (value is None or value == "" or value == []) and "fallback" in mapping:
            value = _get_nested(full_result, mapping["fallback"])

        # 特殊格式化
        fmt = mapping.get("format")
        if fmt:
            if isinstance(fmt, str) and fmt.startswith("_format_"):
                formatter = globals().get(fmt)
                if formatter:
                    value = formatter(value)
            elif callable(fmt):
                value = fmt(value)

        # 最终 fallback
        if value is None or value == "" or value == []:
            value = "未找到"

        # 包装成新 shape：标量/数组分别用 value|items + source_page|source_pages
        # page 在 fallback 路径下为 None
        k01_k14[key] = make_k_field(value, source_page=None)

    return k01_k14
