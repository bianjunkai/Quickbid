# QuickBid 标书制作工具

医院信息化投标文件智能生成工具，采用「确认驱动对话」模式 + 多 Agent 协作架构。

> AI 做一步 → 用户确认/纠正 → 继续。用户说什么，系统就处理什么。

## 技术栈

- **Python FastAPI** — REST API + 对话逻辑
- **SQLAlchemy + SQLite** — 本地数据库
- **Vue 3 + Element Plus** — Web 前端
- **PyMuPDF** — PDF 解析
- **python-docx** — Word 导出
- **DeepSeek API** — AI Agent（Parser / Matcher / Generator / Reviewer / SubBid）

## 快速开始

### 环境准备

使用 [uv](https://docs.astral.sh/uv/) 管理 Python 虚拟环境：

```bash
# 安装 uv（如未安装）
pip install uv

# 创建虚拟环境并安装依赖
uv venv
uv pip install -r requirements.txt

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
```

### 启动

```bash
# CLI 对话模式
python cli.py

# REST API 模式（Web 前端需要）
python main.py

# Web 前端（另开终端）
cd web && npm install && npm run dev
```

## 工作流

```
① 新建项目 → ② 上传招标文件 → ③ ParserAgent 解析 → 用户确认
→ ④ MatcherAgent 匹配材料 → 用户确认/替换
→ ⑤ GeneratorAgent 生成初稿 → 用户确认/修改
→ ⑥ ReviewerAgent 终审检查 → ⑦ 导出 Word/PDF
```

## 架构

详见 [docs/technical-design.md](docs/technical-design.md) 和 [docs/multi-agent-architecture.md](docs/multi-agent-architecture.md)。

```
Orchestrator（状态机 + Agent 调度）
  ├── ParserAgent      → K01-K14 结构化提取
  ├── MatcherAgent     → 章节-材料智能匹配
  ├── GeneratorAgent   → 标书初稿生成
  ├── ReviewerAgent    → C01-C10 终审检查（主标+陪标）
  └── SubBidAgent      → 陪标独立生成 → 再审
```

## LICENSE

MIT
