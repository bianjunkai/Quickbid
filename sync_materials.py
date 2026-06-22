#!/usr/bin/env python
"""同步 materials/ 文件夹到数据库。"""
from pathlib import Path
from datetime import datetime

import docx2txt

from models import init_db, get_session, Material

MATERIALS_DIR = Path(__file__).parent / "materials"
STANDARD_CATEGORIES = [
    "01_公司资质",
    "02_业绩案例",
    "03_技术方案",
    "04_实施方案",
    "05_商务文件",
    "06_其他",
]


def sync_materials():
    init_db()
    session = get_session()

    # 统计
    added = 0
    updated = 0
    skipped = 0

    for cat in STANDARD_CATEGORIES:
        cat_dir = MATERIALS_DIR / cat
        if not cat_dir.exists():
            continue

        for file_path in cat_dir.iterdir():
            if file_path.name in (".gitkeep", ".DS_Store") or file_path.is_dir():
                continue

            # 提取文本
            try:
                if file_path.suffix.lower() == ".md":
                    text = file_path.read_text(encoding="utf-8")
                elif file_path.suffix.lower() in (".docx", ".doc"):
                    text = docx2txt.process(str(file_path))
                else:
                    print(f"⚠️  跳过不支持格式: {file_path.name}")
                    skipped += 1
                    continue

                if not text or len(text.strip()) < 10:
                    print(f"⚠️  跳过空文件: {file_path.name}")
                    skipped += 1
                    continue
            except Exception as e:
                print(f"❌ 提取失败: {file_path.name} - {e}")
                skipped += 1
                continue

            # 文件名 → 标题（去掉扩展名）
            title = file_path.stem

            # 检查是否已存在（按 source_file 路径匹配）
            existing = session.query(Material).filter(
                Material.source_file == str(file_path),
                Material.is_deleted == False  # noqa: E712 - SQLAlchemy expression
            ).first()

            if existing:
                # 更新
                existing.content = text
                existing.char_count = len(text)
                existing.updated_at = datetime.utcnow()
                print(f"🔄 更新: {title} ({cat})")
                updated += 1
            else:
                # 新增
                material = Material(
                    title=title,
                    category=cat,
                    description=f"从 {file_path.name} 导入",
                    content=text,
                    content_type="markdown" if file_path.suffix == ".md" else "docx",
                    source_file=str(file_path),
                    char_count=len(text),
                    tags="",
                    ai_summary="",
                )
                session.add(material)
                print(f"✅ 新增: {title} ({cat})")
                added += 1

    session.commit()

    print()
    print(f"📊 同步完成: 新增 {added}, 更新 {updated}, 跳过 {skipped}")

    # 显示当前材料库
    all_materials = session.query(Material).filter(
        Material.is_deleted == False  # noqa: E712 - SQLAlchemy expression
    ).all()
    print(f"📚 当前材料库总数: {len(all_materials)}")
    for m in all_materials:
        print(f"  [{m.id}] {m.title} ({m.category})")


if __name__ == "__main__":
    sync_materials()
