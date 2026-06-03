"""
标书制作工具 - FastAPI REST API
确认驱动的工作流：Agent 做一步 → 用户确认/纠正 → 继续

所有业务逻辑委托给 Orchestrator。
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import init_db, get_session, Project, Tender, Material
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
    allow_credentials=True,
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
    }


@app.delete("/projects/{project_id}")
def delete_project(project_id: int):
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    session.delete(project)
    session.commit()
    return {"message": "项目已删除"}


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

    content = await file.read()
    # 写盘时统一按实际后缀命名（而不是沿用项目里预生成的占位 .pdf 路径）
    base = Path(project.tender_file_path).with_suffix(suffix)
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
        "filename": file.filename,
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
    """Step 2 — 标记语义识别（1 次 LLM，~3-5s）。"""
    state = _parse_state.get(project_id)
    if not state:
        raise HTTPException(400, "请先执行 step1")
    if state["mode"] not in ("full", "auto"):
        # quick / manual 不需要标记语义
        return {"step": 2, "name": "标记语义识别", "status": "skipped", "summary": {}}
    pipeline = _make_pipeline()
    t0 = time.time()
    sem = pipeline.step2_detect_markers(state["full_text"])
    state["marker_semantics"] = sem
    markers = sem.get("detection", {}).get("markers", []) or []
    return {
        "step": 2, "name": "标记语义识别", "status": "done",
        "elapsed_sec": round(time.time() - t0, 2),
        "summary": {
            "marker_types": len(markers),
            "markers": [{"symbol": m.get("symbol"), "semantic": m.get("semantic_label"),
                         "priority": m.get("priority")} for m in markers],
        },
    }


@app.post("/projects/{project_id}/parse/step3")
def parse_step3(project_id: int):
    """Step 3 — 标记精准抽取（多次 LLM，~15-30s）。"""
    state = _parse_state.get(project_id)
    if not state or "marker_semantics" not in state:
        raise HTTPException(400, "请先执行 step2")
    if state["mode"] not in ("full", "auto"):
        return {"step": 3, "name": "标记抽取", "status": "skipped", "summary": {}}
    pipeline = _make_pipeline()
    t0 = time.time()
    extras = pipeline.step3_scan_and_extract(state["full_text"], state["marker_semantics"])
    state["marker_extractions"] = extras
    summary = extras.get("extraction_summary", {})
    return {
        "step": 3, "name": "标记抽取", "status": "done",
        "elapsed_sec": round(time.time() - t0, 2),
        "summary": {
            "total": summary.get("total_marker_occurrences", 0),
            "fatal": len(extras.get("fatal_items", [])),
            "critical": len(extras.get("critical_items", [])),
            "high": len(extras.get("high_items", [])),
            "medium": len(extras.get("medium_items", [])),
            "low": len(extras.get("low_items", [])),
        },
    }


@app.post("/projects/{project_id}/parse/step4")
def parse_step4(project_id: int):
    """Step 4 — 字段分段抽取（10 个模块独立 LLM，~30-60s）。"""
    state = _parse_state.get(project_id)
    if not state or "marker_extractions" not in state:
        raise HTTPException(400, "请先执行 step3")
    if state["mode"] not in ("full", "auto"):
        return {"step": 4, "name": "字段抽取", "status": "skipped", "summary": {}}
    pipeline = _make_pipeline()
    t0 = time.time()
    fields = pipeline.step4_extract_fields(state["full_text"], state["marker_extractions"])
    state["field_results"] = fields
    return {
        "step": 4, "name": "字段抽取", "status": "done",
        "elapsed_sec": round(time.time() - t0, 2),
        "summary": {
            "modules": list(fields.keys()),
            "filled": [k for k, v in fields.items() if v and (isinstance(v, dict) and len(v) > 0 or isinstance(v, list) and len(v) > 0)],
        },
    }


@app.post("/projects/{project_id}/parse/step5")
def parse_step5(project_id: int):
    """Step 5 — 合并校验 + 落库。根据 mode 分支处理。

    Returns:
        包含完整 parsed_data，前端可立即填到 parserResult
    """
    state = _parse_state.get(project_id)
    if not state:
        raise HTTPException(400, "请先执行前面的步骤")
    t0 = time.time()
    project = _get_project_or_404(project_id)
    mode = state["mode"]

    if mode == "full" or mode == "auto":
        # full 路径：合并 + 校验
        if not all(k in state for k in ("marker_semantics", "marker_extractions", "field_results")):
            raise HTTPException(400, "full 模式需要 step2-4 都完成")
        pipeline = _make_pipeline()
        final = pipeline.step5_merge_and_validate(
            state["marker_semantics"], state["marker_extractions"], state["field_results"]
        )
        if not final.get("meta"):
            from agents.parser_agent import ParserAgent  # lazy import 避免循环
            final["meta"] = ParserAgent({})._build_meta(state["file_path"])
        k01_k14 = full_result_to_k01_k14(final)
        output = {**k01_k14, **final, "_mode": "full"}
        elapsed_merge = time.time() - t0
    elif mode == "quick":
        pipeline = _make_pipeline()
        result = pipeline.run_quick(state["file_path"])
        output = {**result, "_mode": "quick"}
        elapsed_merge = time.time() - t0
    elif mode == "manual":
        pages = extract_pages(state["full_text"])
        hits = scan_markers(pages)
        marker_sum = summarize_markers(hits)
        output = {
            "_mode": "manual",
            "meta": {},
            "_text_length": len(state["full_text"]),
            "_text_preview": state["full_text"][:2000],
            "_marker_summary": marker_sum,
        }
        elapsed_merge = time.time() - t0
    else:
        raise HTTPException(400, f"未知 mode: {mode}")

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
        "step": 5, "name": "合并校验", "status": "done",
        "elapsed_sec": round(elapsed_merge, 2),
        "total_elapsed_sec": total_elapsed,
        "summary": {
            "validation_issues": len((output.get("_validation") or {}).get("issues", [])),
        },
        "parsed_data": output,
    }


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
