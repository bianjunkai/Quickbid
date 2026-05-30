"""
标书制作工具 - FastAPI 主程序
确认驱动的工作流：AI 做一步 → 用户确认/纠正 → 继续
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

# ---- 配置加载 ----
_CONFIG_DIR = Path(__file__).parent
CONFIG_PATH = _CONFIG_DIR / "config.yaml"
if not CONFIG_PATH.exists():
    CONFIG_PATH = Path.home() / "tender-tool" / "config.yaml"
os.environ.setdefault("TENDER_CONFIG_PATH", str(CONFIG_PATH))

def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

config = load_config()

PROJECTS_DIR = Path(config["tender_tool"]["projects_dir"]).expanduser()
MATERIALS_DIR = Path(config["tender_tool"]["materials_dir"]).expanduser()
EXPORTS_DIR = Path(config["tender_tool"]["exports_dir"]).expanduser()

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
MATERIALS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ---- FastAPI App ----
app = FastAPI(title="标书制作工具", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- 初始化数据库 ----
init_db()


# ===========================
# Pydantic 模型
# ===========================

class CreateProjectRequest(BaseModel):
    name: str
    tender_file_name: str  # 用户告知文件名，完整路径由系统生成


class TenderParseConfirmRequest(BaseModel):
    project_id: int
    corrections: Optional[dict] = None  # 用户纠正的数据，如 {"budget": 9000000, "deadline": "2026-06-20"}


class MaterialMatchRequest(BaseModel):
    project_id: int
    chapter: str
    action: str  # "confirm" / "replace" / "skip"
    material_id: Optional[int] = None  # replace 时传入


class GenerateDraftRequest(BaseModel):
    project_id: int
    tender_type: str  # "main" / "sub"
    confirmed_chapters: Optional[dict] = None  # 章节 -> material_id 映射


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
    return {"message": "标书制作工具 API", "version": "1.0.0"}


# ---- 项目管理 ----

@app.post("/projects")
def create_project(req: CreateProjectRequest):
    """
    创建新项目。
    流程：用户提供项目名称和招标文件名 → 系统创建目录 → 返回存放路径
    """
    # 创建项目目录
    import re
    safe_name = re.sub(r"[^\w\-]", "_", req.name)
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
    """列出所有项目"""
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
    """获取项目详情"""
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status.value if hasattr(project.status, 'value') else project.status,
        "tender_file_path": project.tender_file_path,
        "project_name": project.project_name,
        "tender_no": project.tender_no,
        "budget": project.budget,
        "deadline": project.deadline.isoformat() if project.deadline else None,
        "open_time": project.open_time.isoformat() if project.open_time else None,
    }


@app.delete("/projects/{project_id}")
def delete_project(project_id: int):
    """删除项目"""
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
    """
    解析招标文件。
    AI 读取 tender_file_path，提取关键信息（K01-K14），存入数据库。
    返回解析结果，等待用户确认。
    """
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    tender_path = Path(project.tender_file_path)
    if not tender_path.exists():
        raise HTTPException(400, f"招标文件不存在：{tender_path}，请先上传文件")

    # TODO: 调用 AI 解析文件
    # 临时返回结构，实际需要调用 DeepSeek API
    parsed = {
        "K01_项目名称": project.name,
        "K02_招标编号": "待提取",
        "K03_招标人信息": "待提取",
        "K04_预算金额": 0,
        "K05_投标截止时间": None,
        "K06_开标时间": None,
        "K07_评分标准": "待提取",
        "K08_技术要求": "待提取",
        "K09_商务资质要求": "待提取",
        "K10_星标项": [],
        "K11_废标条款": [],
        "K12_章节模板要求": "待提取",
        "K13_偏离表要求": "待提取",
        "K14_演示要求": "待提取",
    }

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
    """
    用户确认解析结果（或纠正后确认）。
    corrections: 需要修正的字段，如 {"budget": 9000000, "deadline": "2026-06-15"}
    """
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

    return {
        "message": "信息已确认，接下来帮你匹配材料吗？",
        "next_action": "开始主标材料匹配"
    }


# ---- 材料库管理 ----

@app.get("/materials")
def list_materials(
    category: Optional[str] = None,
    keyword: Optional[str] = None,
):
    """列出材料库材料，支持按分类和关键词筛选"""
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
    """
    添加新材料到材料库。
    通常在材料文件放入 materials/ 目录后调用，更新数据库索引。
    """
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
    return {
        "id": material.id,
        "title": material.title,
        "message": "材料已添加到材料库"
    }


# ---- 标书生成 ----

@app.get("/projects/{project_id}/match")
def match_materials(project_id: int, tender_type: str = "main"):
    """
    AI 分析招标文件章节结构，从材料库推荐匹配材料。
    返回每章节的推荐材料列表，等待用户确认/替换。
    """
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    # TODO: 实际调用 AI 做章节分析 + 材料匹配
    # 临时返回模拟数据
    mock_chapters = [
        {"chapter": "第一章 公司简介", "recommended": [
            {"id": 1, "title": "公司简介模板", "match_score": "高", "reason": "标准公司简介"}
        ]},
        {"chapter": "第二章 业绩案例", "recommended": [
            {"id": 2, "title": "xx省人民医院HIS系统", "match_score": "高", "reason": "三甲医院，HIS系统"}
        ]},
        {"chapter": "第三章 技术方案", "recommended": [
            {"id": 3, "title": "HIS技术方案v2", "match_score": "中", "reason": "版本较新"}
        ]},
    ]

    return {
        "message": "材料匹配完成，请确认每章选择：",
        "chapters": mock_chapters,
        "action_hint": "可以告诉我需要替换哪个章节，或说'继续'进入生成"
    }


@app.post("/projects/{project_id}/generate")
def generate_tender(project_id: int, req: GenerateDraftRequest):
    """
    根据确认的材料生成标书初稿。
    主标：拼接已有材料 + AI 修正冲突
    陪标：AI 全量生成（商务资质除外）
    """
    session = get_session()
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    # 创建标书记录
    tender = Tender(
        project_id=project_id,
        type=req.tender_type,
        status="draft",
    )
    session.add(tender)
    session.commit()
    session.refresh(tender)

    # TODO: 实际调用 AI 生成
    # 1. 读取确认的材料
    # 2. 拼接 + 冲突修正
    # 3. 生成偏离表
    # 4. 保存 draft_path / deviation_path

    project.status = "generating"
    session.commit()

    return {
        "tender_id": tender.id,
        "message": f"{'主标' if req.tender_type == 'main' else '陪标'}初稿已生成",
        "draft_preview": "...（初稿预览）",
        "action_hint": "请查看初稿，有需要修改的地方告诉我"
    }


@app.post("/tenders/{tender_id}/review")
def review_tender(tender_id: int):
    """
    执行终审检查（10项检查清单）。
    返回检查报告，用户处理完毕后可导出。
    """
    session = get_session()
    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(404, "标书不存在")

    # TODO: 实际执行10项检查
    mock_report = {
        "C01_名称一致性": {"status": "pass", "issues": []},
        "C02_产品名称一致性": {"status": "pass", "issues": []},
        "C03_时间一致性": {"status": "warning", "issues": ["第3章和第7章工期描述不一致"]},
        "C04_期限一致性": {"status": "pass", "issues": []},
        "C05_金额一致性": {"status": "pass", "issues": []},
        "C06_人员一致性": {"status": "pass", "issues": []},
        "C07_章节完整性": {"status": "pass", "issues": []},
        "C08_星标项完整性": {"status": "pass", "issues": []},
        "C09_废标条款自查": {"status": "pass", "issues": []},
        "C10_资质引用有效性": {"status": "pass", "issues": []},
    }

    return {
        "tender_id": tender_id,
        "report": mock_report,
        "summary": {"high": 0, "medium": 1, "low": 0},
        "message": "终审检查完成，发现 1 个警告项",
        "action_hint": "要我一键修正，还是你手动处理？"
    }


# ---- 导出 ----

@app.post("/tenders/{tender_id}/export")
def export_tender(tender_id: int, req: ExportRequest):
    """
    导出标书为 Markdown / Word / PDF。
    """
    session = get_session()
    tender = session.get(Tender, tender_id)
    if not tender:
        raise HTTPException(404, "标书不存在")

    # TODO: 实际执行导出
    # - Markdown: 直接读取 draft_path
    # - Word: python-docx 转换
    # - PDF: WeasyPrint 或 LibreOffice 转换

    export_path = EXPORTS_DIR / f"tender_{tender_id}.{req.format}"

    return {
        "message": f"已导出为 {req.format}",
        "export_path": str(export_path),
        "download_url": f"/downloads/{tender_id}/{req.format}"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
