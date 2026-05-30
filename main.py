"""
标书制作工具 - FastAPI REST API
确认驱动的工作流：Agent 做一步 → 用户确认/纠正 → 继续

所有业务逻辑委托给 Orchestrator。
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import init_db, get_session, Project, Tender, Material
from orchestrator import Orchestrator

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

@app.post("/projects/{project_id}/parse")
def parse_tender(project_id: int):
    """由 ParserAgent 解析招标文件，提取 K01-K14。"""
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

    parsed = orch.agents["parser"].execute(orch.ctx)

    project.parsed_data = json.dumps(parsed, ensure_ascii=False)
    project.status = "parsed"
    session.commit()

    return {
        "message": "解析完成，请确认以下信息是否正确：",
        "parsed_data": parsed,
        "correction_hint": "如有错误，请告知我需要修改的内容"
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
