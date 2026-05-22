# 标书制作工具

医院信息化投标文件智能生成工具，采用「确认驱动对话」模式。

## 核心思路

传统按钮操作 → **对话驱动工作流**

> AI 做一步 → 用户确认/纠正 → 继续

用户说什么，系统就处理什么。不需要意图识别。

## 目录结构（固化）

```
tender-tool/
├── config.yaml           # 全局配置
├── models.py             # SQLAlchemy 数据模型
├── main.py               # FastAPI REST API
├── cli.py                # 对话管理器（核心）
├── materials/            # 材料库（永久积累）
│   ├── 01_公司资质/
│   ├── 02_业绩案例/
│   ├── 03_技术方案/
│   ├── 04_实施方案/
│   ├── 05_商务文件/
│   └── 06_其他/
├── projects/             # 项目目录（每个项目一个文件夹）
└── exports/              # 导出文件
```

## 工作流

```
① 新建项目 → ② 上传招标文件 → ③ AI解析，用户确认
→ ④ AI匹配材料，用户确认/替换 → ⑤ 生成初稿，用户确认/修改
→ ⑥ 终审检查 → ⑦ 导出 Word/PDF
```

## 快速开始

```bash
# 安装依赖
pip install fastapi uvicorn sqlalchemy pydantic pyyaml python-docx pymupdf

# 启动对话模式
python cli.py

# 或者启动 REST API
python main.py
```

## 对话示例

```
👤 新建项目：xx医院HIS投标
🤖 项目已创建，请将招标文件放到：
   ~/tender-tool/projects/20260522_xx医院HIS投标/tender.pdf
   放好后告诉我「放好了」

👤 放好了
🤖 解析完成！关键信息如下...
   请确认以上信息是否正确

👤 预算应该是900万
🤖 已修正。材料匹配结果...
   要说「继续」进入生成，或者告诉我需要换哪个章节

👤 继续
🤖 主标初稿已生成！...
   输入「终审」进行检查，或「修改」告诉我需要改的地方

👤 终审
🤖 终审检查报告：⚠️ 警告 1 项
   要说「自动修正」还是你手动改？

👤 自动修正
🤖 已修正。现在可以导出了

👤 导出Word
🤖 已导出为 WORD，保存路径：...
```

## 技术栈

- **Python FastAPI** — REST API + 对话逻辑
- **SQLAlchemy + SQLite** — 本地数据库
- **PyMuPDF** — PDF 解析
- **python-docx** — Word 导出
- **DeepSeek API** — AI 解析与生成（待接入）

## LICENSE

MIT
