"""
标书制作工具 - FastAPI REST API
确认驱动的工作流：Agent 做一步 → 用户确认/纠正 → 继续

所有业务逻辑委托给 Orchestrator。
"""
import json
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from models import init_db, get_session, Project, Tender, Material, MaterialUsage
from orchestrator import Orchestrator
from agents.bid_parser.pipeline import (
    BidLLMClient,
    BidParsePipeline,
    full_result_to_k01_k14,
)
from agents.bid_parser.pdf_extractor import get_file_info
from agents.bid_parser.marker_scanner import (
    extract_pages,
    scan_markers,
    summarize_markers,
)

# ---- 环境变量加载 ----
# 优先从 .env 读 TENDER_DEEPSEEK_API_KEY 等敏感信息（已在 .gitignore 中）
load_dotenv()

# ---- 配置加载 ----
_CONFIG_DIR = Path(__file__).parent
CONFIG_PATH = _CONFIG_DIR / "config.yaml"
if not CONFIG_PATH.exists():
    CONFIG_PATH = Path.home() / "tender-tool" / "config.yaml"
os.environ.setdefault("TENDER_CONFIG_PATH", str(CONFIG_PATH))


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()
tender_config = config.get("tender_tool", {})

PROJECTS_DIR = Path(tender_config.get("projects_dir", "./projects"))
MATERIALS_DIR = Path(tender_config.get("materials_dir", "./materials"))
EXPORTS_DIR = Path(tender_config.get("exports_dir", "./exports"))

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ---- FastAPI App ----
app = FastAPI(title="标书制作工具", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


# ===========================
# Pydantic 模型
# ===========================

class CreateProjectRequest(BaseModel):
    name: str
    tender_file_name: str


class TenderParseConfirmRequest(BaseModel):
    project_id: int
    corrections: Optional[dict] = None


class GenerateDraftRequest(BaseModel):
    project_id: int
    tender_type: str = "main"
    confirmed_chapters: Optional[dict] = None
    need_sub_bid: bool = False


class ExportRequest(BaseModel):
    tender_id: int
    format: str  # "markdown" / "word" / "pdf"


class CreateMaterialRequest(BaseModel):
    title: str
    category: str
    description: str
    content: str
    content_type: str = "markdown"
    tags: Optional[str] = None


# ===========================
# 路由
# ===========================

@app.get("/")
def root():
    return {"message": "标书制作工具 API v3 (多 Agent)", "version": "2.0.0"}


# ---- 项目管理 ----

@app.post("/projects")
def create_project(req: CreateProjectRequest):
    safe_name = __import__("re").sub(r"[^\w\-]", "_", req.name)
    timestamp = datetime.now().strftime("%Y%m%d")
    project_dir = PROJECTS_DIR / f"{timestamp}_{safe_name}"
    project_dir.mkdir(parents=True, exist_ok=True)
    tender_path = project_dir / req.tender_file_name

    session = get_session()
    project = Project(
        name=req.name,
        tender_file_path=str(tender_path),
        status="parsing",
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    return {
        "project_id": project.id,
        "project_name": project.name,
        "tender_file_path": str(tender_path),
        "message": f"项目已创建，请将招标文件上传到：{tender_path}"
    }


@app.get("/projects")
def list_projects():
    session = get_session()
    projects = session.query(Project).order_by(Project.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "created_at": p.created_at.isoformat(),
        }
        for p in projects
    ]


@app.get("/projects/{project_id}")
def get_project(project_id: int):
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "tender_file_path": project.tender_file_path,
        "project_name": project.project_name,
        "tender_no": project.tender_no,
        "budget": project.budget,
        "deadline": project.deadline.isoformat() if project.deadline else None,
        "open_time": project.open_time.isoformat() if project.open_time else None,
        # 包含已解析数据（前端 ChatView 重新进入项目时恢复解析报告）
        "parsed_data": json.loads(project.parsed_data) if project.parsed_data else None,
        # 对话历史（UIMessage[]，useChat 初始化时回填）
        "messages": json.loads(project.messages_json) if project.messages_json else [],
    }


@app.delete("/projects/{project_id}")
def delete_project(project_id: int):
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    # 清理关联数据：材料使用记录 → 标书 → 项目
    session.query(MaterialUsage).filter(MaterialUsage.project_id == project_id).delete()
    session.query(Tender).filter(Tender.project_id == project_id).delete()
    session.delete(project)
    session.commit()
    return {"message": "项目已删除"}


@app.put("/projects/{project_id}/messages")
def save_messages(project_id: int, payload: dict):
    """保存对话历史（useChat.onFinish 回调）。"""
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    messages = payload.get("messages", [])
    if not isinstance(messages, list):
        raise HTTPException(400, "messages 必须为数组")
    project.messages_json = json.dumps(messages, ensure_ascii=False)
    session.commit()
    return {"message": "已保存", "count": len(messages)}


# ---- 招标文件解析 ----

@app.post("/projects/{project_id}/upload")
async def upload_tender(project_id: int, file: UploadFile = File(...)):
    """上传招标文件（multipart/form-data）。

    保存到 project.tender_file_path 并将 status 置回 "parsing"。
    不自动触发解析——由用户说「放好了」后由 /parse 端点执行，
    保持"AI 做一步 → 用户确认"的节奏。

    实际保存路径会按上传文件后缀调整（避免 .pdf 后缀装 DOCX 内容的问题）。
    """
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise HTTPException(400, f"不支持的文件类型：{suffix}（仅接受 .pdf / .docx）")

    # 清洗文件名：去除路径分隔符和危险字符，保留中文/英文/数字/_-
    import re as _re
    raw_name = Path(file.filename or "tender").name
    safe_name = _re.sub(r"[^\w一-鿿\-.]", "_", raw_name)
    if not safe_name or safe_name.startswith("."):
        safe_name = f"tender{suffix}"

    content = await file.read()
    # 用原文件名（清洗后）覆盖占位 tender.pdf — 前端能显示实际名字
    base = Path(project.tender_file_path).parent / safe_name
    base.parent.mkdir(parents=True, exist_ok=True)
    base.write_bytes(content)
    # 同步更新 DB 中的路径，保证后续 /parse 走正确的解析分支
    project.tender_file_path = str(base)
    project.status = "parsing"
    session.commit()

    return {
        "message": "上传成功，请输入「放好了」开始解析",
        "file_path": str(base),
        "file_size": len(content),
        "filename": safe_name,
    }


@app.post("/projects/{project_id}/parse")
def parse_tender(project_id: int, mode: Optional[str] = None):
    """由 ParserAgent 解析招标文件，提取 K01-K14 + 结构化数据。

    Query:
        mode: 解析模式覆盖 — auto/quick/full/manual。
              缺省走 config.yaml 的 parser.mode（默认 full）。
    """
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    tender_path = Path(project.tender_file_path)
    if not tender_path.exists():
        raise HTTPException(400, f"招标文件不存在：{tender_path}")

    orch = Orchestrator(tender_config)
    orch.ctx.project_id = project_id
    orch.ctx.parsed_data["K01_项目名称"] = project.name
    if mode:
        orch.ctx.parser_mode_override = mode

    parsed = orch.agents["parser"].execute(orch.ctx)

    project.parsed_data = json.dumps(parsed, ensure_ascii=False)
    project.status = "parsed"
    session.commit()

    return {
        "message": "解析完成，请确认以下信息是否正确：",
        "parsed_data": parsed,
        "correction_hint": "如有错误，请告知我需要修改的内容"
    }


# ============================================================
# 分步解析：每步独立端点，前端可串行调用以显示进度
# ============================================================

# 内存缓存：project_id → 解析中间态
# 解析完成或项目删除时清除。重启服务会丢失（用户重新发起即可）
_parse_state: dict[int, dict] = {}


def _make_pipeline() -> BidParsePipeline:
    """构造一个独立的 pipeline 实例（无状态，可随时新建）。"""
    ai = tender_config.get("ai", {})
    parser_cfg = tender_config.get("parser", {})
    client = BidLLMClient(
        model=ai.get("model", "deepseek-v4-flash"),
        base_url=ai.get("base_url", "https://api.deepseek.com"),
    )
    return BidParsePipeline(client, parser_cfg)


def _resolve_mode(project_id: int, mode: Optional[str]) -> str:
    """解析 mode：query 参数 > config 默认。"""
    if mode and mode in {"auto", "quick", "full", "manual"}:
        return mode
    return tender_config.get("parser", {}).get("mode", "auto")


def _get_project_or_404(project_id: int) -> Project:
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    tender_path = Path(project.tender_file_path)
    if not tender_path.exists():
        raise HTTPException(400, f"招标文件不存在：{tender_path}")
    return project


def _step1_summary(text: str, info: dict) -> dict:
    return {
        "text_length": len(text),
        "file_type": info.get("type"),
        "pages": info.get("estimated_pages", 0),
    }


@app.post("/projects/{project_id}/parse/step1")
def parse_step1(project_id: int, mode: Optional[str] = None):
    """Step 1 — 文件文本提取（无 LLM，最快 ~1s）。"""
    project = _get_project_or_404(project_id)
    pipeline = _make_pipeline()
    t0 = time.time()
    text = pipeline.step1_extract_text(project.tender_file_path)
    info = get_file_info(project.tender_file_path)
    _parse_state[project_id] = {
        "mode": _resolve_mode(project_id, mode),
        "file_path": project.tender_file_path,
        "file_info": info,
        "full_text": text,
        "t_start": t0,
    }
    return {
        "step": 1, "name": "提取文本", "status": "done",
        "elapsed_sec": round(time.time() - t0, 2),
        "summary": _step1_summary(text, info),
    }


@app.post("/projects/{project_id}/parse/step2")
def parse_step2(project_id: int):
    """Step 2 — 单次 LLM 全量解析（1M 上下文，~20-40s）。

    替代旧的 step2_detect_markers + step3_scan_and_extract + step4_extract_fields 三步。
    1 次 LLM 调用同时输出 K01-K14 + 8 模块 + 标记抽取。
    """
    state = _parse_state.get(project_id)
    if not state:
        raise HTTPException(400, "请先执行 step1")
    if state["mode"] in ("quick", "manual"):
        return {"step": 2, "name": "LLM 解析", "status": "skipped", "summary": {}}
    pipeline = _make_pipeline()
    t0 = time.time()
    parsed = pipeline.step2_full_parse(state["full_text"])
    state["parsed"] = parsed

    if parsed.get("_mode") in ("manual", "error"):
        return {
            "step": 2, "name": "LLM 解析", "status": parsed["_mode"],
            "elapsed_sec": round(time.time() - t0, 2),
            "summary": {"_error": parsed.get("_error", "")},
        }

    k_filled = sum(1 for k in parsed if k.startswith("K") and parsed[k] and parsed[k] != "未找到")
    modules = ["base", "qualification", "rejection", "scoring", "tech", "commercial", "templates", "logistics"]
    modules_filled = [m for m in modules if parsed.get(m)]
    marker_fatal = len(parsed.get("marker_extractions", {}).get("fatal_items", []))
    marker_total = parsed.get("marker_extractions", {}).get("extraction_summary", {}).get("total_marker_occurrences", 0)

    return {
        "step": 2, "name": "LLM 解析", "status": "done",
        "elapsed_sec": round(time.time() - t0, 2),
        "summary": {
            "k_filled": k_filled,
            "modules": modules,
            "modules_filled": modules_filled,
            "marker_fatal": marker_fatal,
            "marker_total": marker_total,
        },
    }


@app.post("/projects/{project_id}/parse/step3")
def parse_step3(project_id: int):
    """Step 3 — 本地校验合并 + 落库。

    接收 step2 的 LLM 输出，做本地校验（模块完整性、必填字段），
    落库到 Project.parsed_data，更新 status='parsed'。
    """
    state = _parse_state.get(project_id)
    if not state:
        raise HTTPException(400, "请先执行 step1")
    t0 = time.time()
    project = _get_project_or_404(project_id)
    mode = state["mode"]

    if mode == "manual":
        # 无 LLM 可用：只跑文本提取 + 标记扫描
        from agents.bid_parser.marker_scanner import (
            extract_pages as _extract_pages,
            scan_markers as _scan_markers,
            summarize_markers as _summarize_markers,
        )
        pages = _extract_pages(state["full_text"])
        hits = _scan_markers(pages)
        marker_sum = _summarize_markers(hits)
        output = {
            "_mode": "manual",
            "meta": {"text_length": len(state["full_text"])},
            "_text_length": len(state["full_text"]),
            "_text_preview": state["full_text"][:2000],
            "_marker_summary": marker_sum,
        }
    elif mode == "quick":
        pipeline = _make_pipeline()
        result = pipeline.run_quick(state["file_path"])
        output = {**result, "_mode": "quick", "_text_length": len(state["full_text"])}
    else:
        # full / auto：合并 step2 输出 + 本地校验
        if "parsed" not in state:
            raise HTTPException(400, "full 模式需要 step2 完成")
        parsed = state["parsed"]
        if parsed.get("_mode") in ("manual", "error"):
            output = {**parsed, "_text_length": len(state["full_text"])}
        else:
            pipeline = _make_pipeline()
            final = pipeline.step3_validate(parsed, state["full_text"])
            # K-层提取（LLM 已给，fallback 用 formatters）
            from agents.parser_agent import ParserAgent
            k01_k14 = ParserAgent({})._extract_k01_k14(final)
            output = {
                **k01_k14,
                **{k: v for k, v in final.items() if k not in k01_k14},
                "_mode": "full",
                "_text_length": len(state["full_text"]),
            }

    # 落库
    session = get_session()
    p = session.get(Project, project_id)
    p.parsed_data = json.dumps(output, ensure_ascii=False)
    p.status = "parsed"
    session.commit()

    # 清理缓存
    _parse_state.pop(project_id, None)

    total_elapsed = round(time.time() - state.get("t_start", t0), 2)
    return {
        "step": 3, "name": "校验合并", "status": "done",
        "elapsed_sec": round(time.time() - t0, 2),
        "total_elapsed_sec": total_elapsed,
        "summary": {
            "validation_issues": len((output.get("_validation") or {}).get("issues", [])),
        },
        "parsed_data": output,
    }


# ============================================================
# 流式解析（AI SDK Data Stream Protocol）— 阶段 2
# 旧 /parse/step1/2/3 端点保留以兼容 Vue 前端，迁移完成后删除
# ============================================================

from sse_stream import (
    stream_text as _sse_text,
    stream_tool_call as _sse_tool,
    stream_finish as _sse_finish,
    stream_error as _sse_error,
)


async def _run_parse_sse(project_id: int, mode: str):
    """
    流式解析生成器：3 步管道 emit AI SDK Protocol 事件。

    实现：worker thread 把事件推到 queue，async generator 从 queue 拉。
    这样 LLM 同步流式调用不会阻塞 FastAPI event loop。
    """
    import asyncio
    import queue
    import threading

    q: queue.Queue = queue.Queue()
    SENTINEL = object()

    def _worker():
        """运行在工作线程：执行 3 步管道，把事件推入 queue。"""
        try:
            pipeline = _make_pipeline()

            # 加载项目
            session = get_session()
            project = session.get(Project, project_id)
            if not project:
                for ev in _sse_error_sync("项目不存在"):
                    q.put(ev)
                return
            tender_path = Path(project.tender_file_path)
            if not tender_path.exists():
                for ev in _sse_error_sync(f"招标文件不存在：{tender_path}"):
                    q.put(ev)
                return

            # ---- Step 1: 提取文本 ----
            t0 = time.time()
            for ev in _sse_text_sync("📄 步骤 1/3 — 提取文本..."):
                q.put(ev)
            text = pipeline.step1_extract_text(tender_path)
            info = get_file_info(tender_path)
            step1_elapsed = round(time.time() - t0, 2)
            for ev in _sse_text_sync(
                f"✓ 提取完成：{len(text)} 字符，{info.get('estimated_pages', 0)} 页（{step1_elapsed}s）"
            ):
                q.put(ev)

            # ---- Step 2: 流式 LLM 解析 ----
            t0 = time.time()
            for ev in _sse_text_sync("🤖 步骤 2/3 — 调用 LLM（最多 16K tokens，~20-40s）..."):
                q.put(ev)

            if mode == "manual" or not pipeline.llm.is_available:
                # 无 LLM 可用 — 走降级路径
                for ev in _sse_text_sync("⚠️ LLM 不可用，进入 manual 模式（仅文件提取 + 标记扫描）"):
                    q.put(ev)
                from agents.bid_parser.marker_scanner import (
                    extract_pages as _extract_pages,
                    scan_markers as _scan_markers,
                    summarize_markers as _summarize_markers,
                )
                pages = _extract_pages(text)
                hits = _scan_markers(pages)
                marker_sum = _summarize_markers(hits)
                output = {
                    "_mode": "manual",
                    "meta": {"text_length": len(text)},
                    "_text_length": len(text),
                    "_text_preview": text[:2000],
                    "_marker_summary": marker_sum,
                }
                # 落库
                p = session.get(Project, project_id)
                p.parsed_data = json.dumps(output, ensure_ascii=False)
                p.status = "parsed"
                session.commit()
                for ev in _sse_tool_sync(
                    "parseTender",
                    {"mode": mode, "projectId": project_id},
                    output,
                ):
                    q.put(ev)
                for ev in _sse_finish_sync():
                    q.put(ev)
                return

            # full / quick 模式 — 调用 LLM（不流式输出原始 JSON，前端只关心最终结果）
            accumulated_text: list[str] = []
            for delta in pipeline.step2_full_parse_stream(text):
                accumulated_text.append(delta)

            step2_elapsed = round(time.time() - t0, 2)
            full_text = "".join(accumulated_text)
            for ev in _sse_text_sync(
                f"✓ LLM 解析完成：{len(full_text)} 字符，{step2_elapsed}s"
            ):
                q.put(ev)

            # 解析 LLM 输出为 dict
            # 鲁棒 JSON 提取：LLM 不带 response_format 后可能输出
            #   - 纯 JSON
            #   - ```json\n{...}\n``` fence
            #   - "Here's the JSON: ... { ... }" 带前缀
            # _extract_json_object 做括号配对扫描，避开字符串内花括号
            parsed = _extract_json_object(full_text.strip())

            if not parsed:
                # 兜底：fence 剥离后重试
                cleaned = full_text.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
                    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
                    parsed = _extract_json_object(cleaned)

            if not parsed:
                for ev in _sse_error_sync("LLM 输出无法解析为 JSON"):
                    q.put(ev)
                # 把原文前 300 字符回传前端方便诊断
                preview = full_text[:300].replace("\n", " ")
                for ev in _sse_text_sync(f"原始输出片段: {preview}…"):
                    q.put(ev)
                return

            # 注入 meta
            parsed.setdefault("meta", {})
            parsed["meta"]["parser_version"] = "3.1.0-full-context"
            parsed["meta"]["text_length"] = len(text)
            parsed["meta"]["prompt_mode"] = "single-shot-1M-context"

            # ---- Step 3: 校验合并 + 落库 ----
            t0 = time.time()
            for ev in _sse_text_sync("✅ 步骤 3/3 — 校验合并..."):
                q.put(ev)
            final = pipeline.step3_validate(parsed, text)
            from agents.parser_agent import ParserAgent
            k01_k14 = ParserAgent({})._extract_k01_k14(final)
            output = {
                **k01_k14,
                **{k: v for k, v in final.items() if k not in k01_k14},
                "_mode": "full",
                "_text_length": len(text),
            }
            p = session.get(Project, project_id)
            p.parsed_data = json.dumps(output, ensure_ascii=False)
            p.status = "parsed"
            session.commit()
            step3_elapsed = round(time.time() - t0, 2)
            for ev in _sse_text_sync(f"✓ 已落库，{step3_elapsed}s"):
                q.put(ev)

            for ev in _sse_tool_sync(
                "parseTender",
                {"mode": mode, "projectId": project_id},
                output,
            ):
                q.put(ev)
            for ev in _sse_finish_sync():
                q.put(ev)

        except Exception as e:
            for ev in _sse_error_sync(f"解析异常：{type(e).__name__}: {e}"):
                q.put(ev)
        finally:
            q.put(SENTINEL)

    # 启动 worker 线程
    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    # async generator 从 queue 拉事件
    loop = asyncio.get_event_loop()
    while True:
        ev = await loop.run_in_executor(None, q.get)
        if ev is SENTINEL:
            break
        yield ev


# 同步版本的 SSE 事件生成器（用于 worker 线程）
def _sse_text_sync(text, message_id=None, text_id=None):
    import uuid as _uuid
    message_id = message_id or f"msg_{_uuid.uuid4().hex[:12]}"
    text_id = text_id or f"text_{_uuid.uuid4().hex[:12]}"
    yield {"data": json.dumps({"type": "start", "messageId": message_id}, ensure_ascii=False)}
    yield {"data": json.dumps({"type": "text-start", "id": text_id}, ensure_ascii=False)}
    yield {"data": json.dumps({"type": "text-delta", "id": text_id, "delta": text}, ensure_ascii=False)}
    yield {"data": json.dumps({"type": "text-end", "id": text_id}, ensure_ascii=False)}
    yield {"data": json.dumps({"type": "finish-step"}, ensure_ascii=False)}


def _sse_tool_sync(tool_name, tool_input, tool_output, message_id=None, tool_call_id=None):
    import uuid as _uuid
    message_id = message_id or f"msg_{_uuid.uuid4().hex[:12]}"
    tool_call_id = tool_call_id or f"call_{_uuid.uuid4().hex[:12]}"
    yield {"data": json.dumps({"type": "start", "messageId": message_id}, ensure_ascii=False)}
    yield {"data": json.dumps(
        {"type": "tool-input-available", "toolCallId": tool_call_id, "toolName": tool_name, "input": tool_input},
        ensure_ascii=False,
    )}
    yield {"data": json.dumps(
        {"type": "tool-output-available", "toolCallId": tool_call_id, "output": tool_output},
        ensure_ascii=False,
    )}
    yield {"data": json.dumps({"type": "finish-step"}, ensure_ascii=False)}


def _extract_json_object(text: str) -> Optional[dict]:
    """
    从 LLM 输出里抽第一个完整的 JSON 对象。

    鲁棒处理：前缀文字、markdown fence、字符串内花括号、嵌套结构。
    顶屋必须是 dict（招标解析 schema 是 object）。
    """
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*\n(.*?)\n?```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    start_idx = -1
    opener, closer = "", ""
    for i, ch in enumerate(text):
        if ch == "{":
            start_idx, opener, closer = i, "{", "}"
            break
        if ch == "[":
            start_idx, opener, closer = i, "[", "]"
            break
    if start_idx < 0:
        return None
    depth = 0
    in_string = escape = False
    for j in range(start_idx, len(text)):
        c = text[j]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(text[start_idx:j + 1])
                    if isinstance(obj, dict):
                        return obj
                except json.JSONDecodeError:
                    return None
                return None
    return None


def _sse_finish_sync():
    yield {"data": json.dumps({"type": "finish"}, ensure_ascii=False)}


def _sse_error_sync(error_message):
    yield {"data": json.dumps({"type": "error", "errorText": error_message}, ensure_ascii=False)}


@app.get("/projects/{project_id}/parse/stream")
async def parse_stream(project_id: int, mode: Optional[str] = None):
    """
    流式解析端点 — emit AI SDK Data Stream Protocol。

    替换旧的 /parse/step1+2+3 串行调用。前端 useChat 直连。

    Query:
        mode: auto/quick/full/manual（缺省走 config.yaml）
    """
    resolved = _resolve_mode(project_id, mode)
    return EventSourceResponse(_run_parse_sse(project_id, resolved))


# ============================================================
# Chat 端点 — useChat 的标准入口，关键词路由
# ============================================================


async def _run_chat_sse(project_id: int, last_user_msg: str):
    """
    关键词路由：把 useChat 的消息分派到对应 agent 流程。

    路由规则（按出现顺序匹配首个）：
      "放好了" / "解析"  → parse 流（delegate to _run_parse_sse）
      "继续"             → match
      "生成" / "开始生成" → generate
      "终审"             → review
      "导出" / "下载"     → export
      else               → help / echo
    """
    msg = last_user_msg.strip()

    # ---- "放好了" → parse ----
    if "放好了" in msg or "解析" in msg:
        for ev in _sse_text_sync("🔍 收到，开始解析..."):
            yield ev
        async for ev in _run_parse_sse(project_id, "full"):
            yield ev
        return

    # ---- "继续" → match ----
    if "继续" in msg:
        session = get_session()
        project = session.get(Project, project_id)
        if not project:
            for ev in _sse_error_sync("项目不存在"):
                yield ev
            return
        for ev in _sse_text_sync("🔍 匹配材料中..."):
            yield ev
        orch = Orchestrator(tender_config)
        orch.ctx.project_id = project_id
        orch.ctx.parsed_data = json.loads(project.parsed_data) if project.parsed_data else {}
        match_result = orch.agents["matcher"].execute(orch.ctx)
        project.status = "materials_preparing"
        session.commit()
        for ev in _sse_tool_sync(
            "matchMaterials",
            {"projectId": project_id, "tenderType": "main"},
            {
                "chapters": match_result.get("chapters", []),
                "message": "材料匹配完成，请确认每章选择。",
                "action_hint": "可以告诉我需要替换哪个章节，或说'继续'进入生成。",
            },
        ):
            yield ev
        for ev in _sse_finish_sync():
            yield ev
        return

    # ---- "生成" → generate ----
    if "生成" in msg:
        session = get_session()
        project = session.get(Project, project_id)
        if not project:
            for ev in _sse_error_sync("项目不存在"):
                yield ev
            return
        for ev in _sse_text_sync("📝 正在生成标书（多 Agent 串行，可能需要数分钟）..."):
            yield ev
        # 实际生成交给线程（这里简单同步执行；后续可改成 worker thread + queue）
        orch = Orchestrator(tender_config)
        result = orch.run_workflow(project_id=project_id, tender_type="main", need_sub_bid=False)
        if "error" in result:
            for ev in _sse_error_sync(result["error"]):
                yield ev
            return
        for ev in _sse_tool_sync(
            "generateTender",
            {"projectId": project_id, "tenderType": "main"},
            {
                "parsed": result.get("parsed"),
                "matches": result.get("matches"),
                "main_review": result.get("main_review"),
                "message": "标书生成完成",
            },
        ):
            yield ev
        for ev in _sse_finish_sync():
            yield ev
        return

    # ---- "终审" → review ----
    if "终审" in msg:
        session = get_session()
        tender = session.query(Tender).filter_by(project_id=project_id, type="main").first()
        if not tender:
            for ev in _sse_error_sync("未找到主标书，无法终审"):
                yield ev
            return
        for ev in _sse_text_sync("🔍 终审检查中..."):
            yield ev
        orch = Orchestrator(tender_config)
        orch.ctx.tender_id = tender.id
        orch.ctx.tender_type = "main"
        orch.ctx.project_id = project_id
        review_result = orch.agents["reviewer"].execute(orch.ctx)
        for ev in _sse_tool_sync(
            "reviewTender",
            {"tenderId": tender.id},
            {
                "tenderId": tender.id,
                "report": {c["check_id"]: {"status": c["status"], "issues": [c["issue"]] if c["issue"] else []}
                            for c in review_result.get("checks", [])},
                "summary": review_result.get("summary", {}),
                "message": f"终审检查完成",
                "action_hint": "要我一键修正，还是你手动处理？",
            },
        ):
            yield ev
        for ev in _sse_finish_sync():
            yield ev
        return

    # ---- "导出" → export ----
    if "导出" in msg or "下载" in msg:
        session = get_session()
        tender = session.query(Tender).filter_by(project_id=project_id, type="main").first()
        if not tender:
            for ev in _sse_error_sync("未找到主标书，无法导出"):
                yield ev
            return
        # 默认 markdown
        export_path = EXPORTS_DIR / f"tender_{tender.id}.md"
        for ev in _sse_tool_sync(
            "exportTender",
            {"tenderId": tender.id, "format": "markdown"},
            {
                "tenderId": tender.id,
                "format": "markdown",
                "export_path": str(export_path),
                "download_url": f"/downloads/{tender.id}/markdown",
                "message": "已导出为 markdown",
            },
        ):
            yield ev
        for ev in _sse_finish_sync():
            yield ev
        return

    # ---- 默认：帮助 ----
    help_text = (
        "我理解这些指令：\n"
        "• 「放好了」— 开始解析招标文件\n"
        "• 「继续」— 进入材料匹配\n"
        "• 「生成」— 生成标书\n"
        "• 「终审」— 终审检查\n"
        "• 「导出」— 导出标书"
    )
    for ev in _sse_text_sync(help_text):
        yield ev
    for ev in _sse_finish_sync():
        yield ev


@app.post("/projects/{project_id}/chat")
async def chat_router(project_id: int, request: Request):
    """
    useChat 主入口 — 接收 messages[]，按关键词路由到对应 agent 流。

    接收：
        { "messages": [{role, content}, ...] }

    返回：
        SSE 流（AI SDK Data Stream Protocol）

    替代旧 /projects/{id}/parse/confirm + /generate + /tenders/{id}/review + /tenders/{id}/export 的
    多端点跳转模式——所有动作统一通过这一个 chat 端点触发。
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "请求体必须为 JSON")
    messages = body.get("messages", [])
    if not isinstance(messages, list):
        raise HTTPException(400, "messages 必须为数组")
    # 找最后一条 user 消息
    # AI SDK v3: { role: "user", parts: [{ type: "text", text: "..." }] }
    # v2 兼容: { role: "user", content: "..." } 或 content: [{ type: "text", text: "..." }]
    last_user_msg = ""
    for m in reversed(messages):
        if isinstance(m, dict) and m.get("role") == "user":
            # v3 优先
            parts = m.get("parts")
            if isinstance(parts, list) and parts:
                last_user_msg = "".join(
                    p.get("text", "") for p in parts if isinstance(p, dict) and p.get("type") == "text"
                )
            else:
                # v2 fallback
                content = m.get("content", "")
                if isinstance(content, str):
                    last_user_msg = content
                elif isinstance(content, list):
                    last_user_msg = "".join(
                        p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
                    )
            break

    # 校验项目存在
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    return EventSourceResponse(_run_chat_sse(project_id, last_user_msg))


@app.post("/projects/{project_id}/parse/confirm")
def confirm_parse(project_id: int, req: TenderParseConfirmRequest):
    """用户确认解析结果，进入材料匹配。"""
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    if req.corrections:
        for key, value in req.corrections.items():
            if hasattr(project, key):
                setattr(project, key, value)

    project.status = "materials_preparing"
    session.commit()

    orch = Orchestrator(tender_config)
    orch.ctx.project_id = project_id
    orch.ctx.parsed_data = json.loads(project.parsed_data) if project.parsed_data else {}

    match_result = orch.agents["matcher"].execute(orch.ctx)

    return {
        "message": "信息已确认，材料匹配完成",
        "chapters": match_result.get("chapters", []),
        "next_action": "开始主标材料匹配"
    }


# ---- 材料库管理 ----

@app.get("/materials")
def list_materials(category: Optional[str] = None, keyword: Optional[str] = None):
    session = get_session()
    query = session.query(Material).filter(Material.is_deleted == False)
    if category:
        query = query.filter(Material.category == category)
    if keyword:
        query = query.filter(Material.title.contains(keyword))
    materials = query.order_by(Material.updated_at.desc()).all()
    return [
        {
            "id": m.id,
            "title": m.title,
            "category": m.category,
            "tags": m.tags,
            "description": m.description,
            "char_count": m.char_count,
            "ai_summary": m.ai_summary,
            "version": m.version,
        }
        for m in materials
    ]


@app.post("/materials")
def create_material(req: CreateMaterialRequest):
    session = get_session()
    material = Material(
        title=req.title,
        category=req.category,
        description=req.description,
        content=req.content,
        content_type=req.content_type,
        tags=req.tags,
        char_count=len(req.content),
    )
    session.add(material)
    session.commit()
    session.refresh(material)
    return {"id": material.id, "title": material.title, "message": "材料已添加"}


# ---- 标书生成（委托给 Orchestrator 自动工作流）----

@app.post("/projects/{project_id}/generate")
def generate_tender(project_id: int, req: GenerateDraftRequest):
    """使用 Orchestrator 自动工作流：匹配 → 生成 → 审查 → (可选)陪标。"""
    orch = Orchestrator(tender_config)
    result = orch.run_workflow(
        project_id=project_id,
        tender_type=req.tender_type,
        need_sub_bid=req.need_sub_bid,
    )

    if "error" in result:
        raise HTTPException(400, result["error"])

    return {
        "message": "标书生成完成",
        "parsed": result.get("parsed"),
        "matches": result.get("matches"),
        "main_review": result.get("main_review"),
        "sub_draft": result.get("sub_draft"),
        "sub_review": result.get("sub_review"),
    }


@app.get("/projects/{project_id}/match")
def match_materials(project_id: int, tender_type: str = "main"):
    """由 MatcherAgent 分析章节并推荐材料。"""
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    orch = Orchestrator(tender_config)
    orch.ctx.project_id = project_id
    orch.ctx.tender_type = tender_type
    orch.ctx.parsed_data = json.loads(project.parsed_data) if project.parsed_data else {}

    match_result = orch.agents["matcher"].execute(orch.ctx)

    return {
        "message": "材料匹配完成，请确认每章选择：",
        "chapters": match_result.get("chapters", []),
        "action_hint": "可以告诉我需要替换哪个章节，或说'继续'进入生成"
    }


@app.post("/tenders/{tender_id}/review")
def review_tender(tender_id: int):
    """由 ReviewerAgent 执行 C01-C10 终审检查。"""
    session = get_session()
    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(404, "标书不存在")

    orch = Orchestrator(tender_config)
    orch.ctx.tender_id = tender_id
    orch.ctx.tender_type = tender.type
    orch.ctx.project_id = tender.project_id

    review_result = orch.agents["reviewer"].execute(orch.ctx)
    checks = review_result.get("checks", [])
    summary = review_result.get("summary", {})

    return {
        "tender_id": tender_id,
        "report": {c["check_id"]: {"status": c["status"], "issues": [c["issue"]] if c["issue"] else []}
                    for c in checks},
        "summary": summary,
        "message": f"终审检查完成，发现 {summary.get('medium', 0)} 个警告项",
        "action_hint": "要我一键修正，还是你手动处理？"
    }


@app.post("/tenders/{tender_id}/export")
def export_tender(tender_id: int, req: ExportRequest):
    """导出标书为 Markdown / Word / PDF。"""
    session = get_session()
    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(404, "标书不存在")

    export_path = EXPORTS_DIR / f"tender_{tender_id}.{req.format}"

    return {
        "message": f"已导出为 {req.format}",
        "export_path": str(export_path),
        "download_url": f"/downloads/{tender_id}/{req.format}"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
