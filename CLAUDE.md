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

# Web 前端（Next.js 15）
cd web-next
npm install
npm run dev                   # http://localhost:3000，API 代理到 :8000（/api/* → :8000/*）
```

无测试套件。

### 测试方式

**默认在 Web UI 上手动测试**——同时启后端 + 前端，在浏览器里点。`python -c "..."` 这种脚本只用于代码改动后的快速冒烟，不是"测试"的替代品。

```bash
# 终端 1：启后端
source .venv/bin/activate && python main.py        # :8000

# 终端 2：启前端
cd web-next && npm run dev                          # :3000（/api/* 代理到 :8000）

# 浏览器打开 http://localhost:3000
```

脚本验证（仅限快速冒烟 / 改 matcher 后的回归）：
```bash
python -c "from models import init_db; init_db(); print('OK')"
```

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
- `main.py` — FastAPI REST API（11 个 REST 端点 + 2 个 SSE 端点），供 `web-next/` 前端调用
- `orchestrator.py` — Agent 编排器，待实现
- `agents/` — 5 个特化 Agent，待实现

### 状态机（ConversationManager）

9 个状态：`IDLE → AWAIT_TENDER_FILE → PARSING → AWAIT_PARSE_CONFIRM → AWAIT_CHAPTER_CONFIRM → GENERATING_DRAFT → AWAIT_DRAFT_CONFIRM → AWAIT_REVIEW_ACTION → AWAIT_EXPORT_CONFIRM → DONE`

三句黄金法则：`继续/确认`（接受）、`修改/换 xxx`（纠正）、`自动修正`（批量修正）

会话持久化到 `.session.json`，支持跨 session 恢复。

### 数据模型（models.py）

SQLAlchemy + SQLite。四个实体：`Project`（status 为纯字符串 `"parsing"` / `"parsed"` / `"materials_preparing"`...）、`Tender`（type=`"main"`\|`"sub"`）、`Material`、`MaterialUsage`。

**重要：** status 和 type 是纯字符串，不是 Enum。`models.py` 中没有 `TenderType` 或 `ProjectStatus` 类。

### Web 前端（web-next/）

Next.js 15 + React 19 + TypeScript + Tailwind 4 + Vercel AI SDK。路由：`/projects`、`/projects/[id]`（chat thread）、`/materials`。

- **SSE 协议**：后端用 `sse-starlette` 实现 [Vercel AI SDK Data Stream Protocol](https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#data-stream-protocol)；前端 `@ai-sdk/react` 的 `useChat` + `DefaultChatTransport` 消费
- **状态机**：保留关键词路由（`放好了`→parse，`继续`→match，`生成`→generate，`终审`→review，`导出`→export），不重做
- **API 代理**：`next.config.ts` 的 `rewrites` 把 `/api/*` 转发到 `http://localhost:8000/*`
- **设计 tokens**：Tailwind 4 `@theme inline` 直接用 CSS 变量（暖色编辑风格，移植自旧 Vue `style.css`）
- **历史**：Vue 3 + Element Plus 版本曾在 `web/` 目录，迁移完成已删除（见 `docs/architecture-decisions.md`）

### SSE 端点（AI SDK Data Stream Protocol）

| 端点 | 方法 | 说明 |
|---|---|---|
| `/projects/{id}/parse/stream` | GET | 旧版三步解析流（保留回退） |
| `/projects/{id}/chat` | POST | 关键词路由主端点，输入 `{messages: [...]}` 输出 SSE |

事件类型：`start` → `text-start`/`text-delta`/`text-end` → `tool-input-available` → `tool-output-available` → `finish-step` → `finish-message` → `finish`。

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
