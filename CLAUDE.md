# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

QuickBid 是医院信息化投标文件智能生成工具。核心范式：**确认驱动对话**（AI 做一步 → 用户确认/纠正 → 继续）。不做意图识别，只做状态路由 + 句式匹配。v3 采用多 Agent 协作架构。

## 开发环境与命令

```bash
# Python 虚拟环境（必须使用 uv，禁止全局安装）
uv venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

# CLI 对话模式
python cli.py

# FastAPI 服务（Web 前端需要）
python main.py                # http://localhost:8000

# Web 前端
cd web
npm install
npm run dev                   # http://localhost:5173，API 代理到 :8000
```

无测试套件。验证方式：`python -c "from models import init_db; print('OK')"` 和手动端到端测试。

## Git 规则

**默认只 `git commit` 本地，不 push。** 仅在用户明确要求（如"推到远端""push""同步到Git"）时才执行 `git push`。

## 架构核心

### 双层入口 → 共享编排器

```
cli.py（CLI 交互层）──┐
                       ├──→ orchestrator.py（Agent 编排器 + 状态机）
main.py（FastAPI）─────┘
                               │
                    ┌──────────┼──────────┬──────────┬──────────┐
                    ▼          ▼          ▼          ▼          ▼
                ParserAgent  Matcher   Generator  Reviewer  SubBidAgent
```

- `cli.py` — 纯交互层，`ConversationManager` 接收用户输入，委托给 Orchestrator
- `main.py` — FastAPI REST API（11 个端点），供 `web/` 前端调用
- `orchestrator.py` — Agent 编排器，待实现
- `agents/` — 5 个特化 Agent，待实现

### 状态机（ConversationManager）

9 个状态：`IDLE → AWAIT_TENDER_FILE → PARSING → AWAIT_PARSE_CONFIRM → AWAIT_CHAPTER_CONFIRM → GENERATING_DRAFT → AWAIT_DRAFT_CONFIRM → AWAIT_REVIEW_ACTION → AWAIT_EXPORT_CONFIRM → DONE`

三句黄金法则：`继续/确认`（接受）、`修改/换 xxx`（纠正）、`自动修正`（批量修正）

会话持久化到 `.session.json`，支持跨 session 恢复。

### 数据模型（models.py）

SQLAlchemy + SQLite。四个实体：`Project`（status 为纯字符串 `"parsing"` / `"parsed"` / `"materials_preparing"`...）、`Tender`（type=`"main"`\|`"sub"`）、`Material`、`MaterialUsage`。

**重要：** status 和 type 是纯字符串，不是 Enum。`models.py` 中没有 `TenderType` 或 `ProjectStatus` 类。

### Web 前端（web/）

Vue 3 + TypeScript + Element Plus + Vite。路由：`/projects`、`/projects/:id`（7 步向导）、`/materials`。API 层 `web/src/api/index.ts` 通过 Vite proxy 调用 FastAPI。`web/src/store/project.ts` 是 Pinia store。

## 目录约定

- `materials/` — 材料库（6 分类：01_公司资质 ~ 06_其他），用 `.gitkeep` 跟踪结构
- `projects/` — 每个项目一个子目录 `<timestamp>_<name>/tender.pdf`
- `exports/` — 导出文件
- `docs/` — 设计文档：`technical-design.md`（核心架构）、`multi-agent-architecture.md`（v3 Agent 设计）、`architecture-decisions.md`（ADR）、`implementation-log.md`（实现日志）

## 关键设计原则

1. **固定路径，不传递路径参数** — 文件路径由系统生成存在 DB
2. **Agent 无状态** — 所有上下文由 Orchestrator 的 `AgentContext` 注入
3. **所有标书产出必经审查** — 主标和陪标都须通过 ReviewerAgent
4. **配置路径** — `config.yaml` 项目本地优先，回退 `~/.tender-tool/`
5. **禁用全局 pip** — 始终通过 `uv` 安装到 `.venv`
