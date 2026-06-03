"""
标书制作工具 - 数据模型
"""
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer,
    String, Text, create_engine
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

class Base(DeclarativeBase):
    pass


class Project(Base):
    """投标项目"""
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    tender_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="parsing")

    # 解析出的关键信息
    project_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    tender_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    budget: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    open_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    parsed_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 对话历史（UIMessage[] 序列化为 JSON）
    messages_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Tender(Base):
    """标书（主标或陪标）"""
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # main / sub
    status: Mapped[str] = mapped_column(String(50), default="draft")

    draft_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    deviation_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    review_report_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Material(Base):
    """已有材料"""
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    source_file: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, default=0)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class MaterialUsage(Base):
    """材料使用记录"""
    __tablename__ = "material_usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    tender_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tenders.id"), nullable=True)
    chapter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---- 数据库初始化 ----

_CONFIG_DIR = Path(__file__).parent
_DEFAULT_DB = _CONFIG_DIR / "tender.db"
if not _DEFAULT_DB.parent.exists():
    _DEFAULT_DB = Path.home() / "tender-tool" / "tender.db"
DB_PATH = os.environ.get("TENDER_DB_PATH", str(_DEFAULT_DB))

def get_engine():
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)

def init_db():
    """初始化数据库 + 轻量迁移（add column if missing）"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    # 轻量迁移：messages_json 是 2026-06 之后加的，旧 DB 缺这列
    with engine.begin() as conn:
        from sqlalchemy import text
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(projects)")).fetchall()]
        if "messages_json" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN messages_json TEXT"))
    return engine

def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
