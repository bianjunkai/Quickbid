# QuickBid 实现日志

## 2026-05-30：Phase 1 — 冗余代码清理

### 已移除

| 文件/目录 | 说明 | 决策依据 |
|-----------|------|----------|
| `Design.md` | 编码损坏（`\&\#34;`、`\n` 字面量），与 `docs/technical-design.md` 重复 | 保留 `docs/` 中版本为唯一真相源 |
| `ui/` 全部 5 个文件 | PyQt5 桌面 GUI（basic_info_page.py, info_page.py, OutlinePage.py, quick_bid.ui, __init__.py） | 与确认驱动对话理念矛盾，数据模型（QObject+dataclass）与 SQLAlchemy 不兼容，零代码共享 |
| `ui_main.py` | pyuic5 从 .ui 自动生成的 UI 代码 | 依赖已删除的 ui/ 包 |
| `core/data_model.py` | PyQt5 QObject+pyqtSignal 数据模型 | 仅被 PyQt5 UI 引用，与 SQLAlchemy models.py 并行且不兼容 |
| ` resources/styles/styles.qss` | Qt 样式表（目录名带前导空格） | 仅 PyQt5 UI 使用，无其他引用 |
| `web/src/components/HelloWorld.vue` | Vite 脚手架默认组件 | 未被任何路由或组件引用 |
| `web/src/assets/vite.svg` | Vite 脚手架资源 | 仅被 HelloWorld.vue 引用 |
| `web/src/assets/vue.svg` | Vite 脚手架资源 | 仅被 HelloWorld.vue 引用 |
| `web/src/assets/hero.png` | Vite 脚手架资源 | 仅被 HelloWorld.vue 引用 |

### 清理后文件结构

```
Quickbid/
├── .gitignore
├── README.md
├── cli.py
├── config.yaml
├── main.py
├── models.py
├── docs/
│   ├── multi-agent-architecture.md   ← v3 架构设计（新增）
│   └── technical-design.md
└── web/                              ← Vue.js 前端（已清理）
```

### 后续待处理

- Phase 2：关键 Bug 修复


## 2026-05-30：Phase 2 — 关键 Bug 修复 + 基础设施

### 修复清单

| Bug | 文件 | 修复内容 |
|-----|------|---------|
| 导入崩溃 | `main.py:14` | 移除 `TenderType, ProjectStatus` 导入（不存在），所有枚举引用替换为字符串字面量 |
| 缺少导入 | `main.py:5` | 添加 `import json` 和 `from datetime import datetime` |
| JSON 序列化 | `main.py:209` | `str(parsed)` → `json.dumps(parsed, ensure_ascii=False)` |
| 枚举属性访问 | `main.py:133,150,264` | `p.status.value if hasattr(...)` → `p.status`（状态是纯字符串） |
| 配置路径硬编码 | `cli.py:14`, `main.py:17` | 优先项目本地 `config.yaml`，回退 `~/.tender-tool/` |
| 数据库路径硬编码 | `models.py:98` | 优先项目本地 `tender.db`，支持 `TENDER_DB_PATH` 环境变量 |
| 配置路径 | `config.yaml` | `~/tender-tool/` → `./` 相对路径 |
| .gitignore 拼写 | `.gitignore` | `.sesion.json` → `.session.json`，添加 `node_modules/` |
| 缺少依赖文件 | — | 创建 `requirements.txt` |
| 缺少运行时目录 | — | 创建 `materials/` (6 分类)、`projects/`、`exports/`、`scripts/` + `.gitkeep` |
| createMaterial 缺失 | `web/src/api/index.ts` | 添加 `createMaterial` 导出 |
| Pinia store 损坏 | `web/src/store/project.ts` | `createProject` 改为调用正确 API，添加缺失的 API imports |
| CSS 冲突 | `web/src/style.css` | Vite scaffold CSS → 最小化 Element Plus 兼容重置 |
| API 参数不匹配 | `main.py:275` | `create_material` 从查询参数改为 Pydantic `CreateMaterialRequest` body |

### 更新后文件结构

```
Quickbid/
├── config.yaml              ← 已更新（相对路径）
├── requirements.txt         ← 新增
├── .gitignore               ← 已修正
├── README.md
├── cli.py                   ← 已修复（配置路径）
├── main.py                  ← 已修复（导入/序列化/API 参数）
├── models.py                ← 已修复（DB 路径 + os import）
├── docs/
│   ├── technical-design.md  ← 已重写（反映当前实际）
│   ├── multi-agent-architecture.md
│   └── implementation-log.md
├── materials/               ← 新增（6 分类 + .gitkeep）
├── projects/                ← 新增（.gitkeep）
├── exports/                 ← 新增（.gitkeep）
├── scripts/                 ← 新增（空目录）
└── web/                     ← 已修复（api/store/style）
```

### 环境约定

- **Python 虚拟环境**：使用 `uv` 管理，禁止安装到全局 Python
  - `uv venv` 创建环境
  - `uv pip install -r requirements.txt` 安装依赖
  - `.venv/`、`.python-version`、`uv.lock` 已加入 .gitignore

### 后续待处理

- Phase 3：多 Agent 框架搭建（agents/ + orchestrator.py）

## 2026-06-03：前端架构迁移 — Stage 2 (SSE 基建 + Next.js 15 + assistant-ui)

### 动机

旧 `web/` (Vue 3 + Element Plus) 在 `parser_agent` 1M 上下文管道下暴露三个结构性问题：

1. 65 秒解析黑屏（无流式 token 反馈）
2. `ParserResultPanel.vue` 519 行单文件，K01-K14 退化为 chat cards
3. `ChatView.vue` 633 行大文件，难以维护

### Stage 2.A — 后端 SSE 基建

| 文件 | 改动 |
|---|---|
| `requirements.txt` | + `sse-starlette>=2.1.3` |
| `agents/bid_parser/pipeline.py` | + `BidLLMClient.chat_stream()` 真流式 LLM；+ `step2_full_parse_stream()` 包装 |
| `sse_stream.py` (新) | `stream_text` / `stream_tool_call` / `stream_finish` / `stream_error` 工具，emit AI SDK Data Stream Protocol |
| `main.py` | + `GET /projects/{id}/parse/stream`（旧三步解析回退）；+ `POST /projects/{id}/chat`（关键词路由主端点）；+ 关键词路由（`放好了/继续/生成/终审/导出`） |
| (内部) | 同步 LLM 阻塞 event loop 问题：用 `threading.Thread` + `queue.Queue` 把同步生成器搬到 worker thread，async 端通过 `loop.run_in_executor` pull |

### Stage 2.B — Next.js 15 壳

| 文件 | 改动 |
|---|---|
| `web-next/` (新) | Next.js 15.5 + React 19 + TS + Tailwind 4 |
| `web-next/next.config.ts` | rewrites `/api/*` → `http://localhost:8000/*` |
| `web-next/app/globals.css` | 移植 `web/src/style.css` 设计 tokens 到 Tailwind 4 `@theme inline` |
| `web-next/app/layout.tsx` | 字体（Cormorant Garamond / Public Sans / JetBrains Mono）+ `lang="zh-CN"` |
| `web-next/lib/api.ts` | fetch 客户端（listProjects / getProject / createProject / uploadTender / listMaterials 等） |
| `web-next/components/sidebar.tsx` | 左侧导航：项目列表 + 材料库 + 新建对话框 |
| `web-next/app/projects/page.tsx` | 项目列表 |
| `web-next/app/projects/[id]/page.tsx` | chat thread（React 19 `use()` 解 params） |
| `web-next/app/materials/page.tsx` | 材料库 CRUD 表格 |

### Stage 2.C — assistant-ui 集成

| 文件 | 改动 |
|---|---|
| `web-next/components/chat-thread.tsx` | 重写：`useChat` + `DefaultChatTransport` 绑 `/api/projects/{id}/chat` |
| `web-next/components/chat-header.tsx` (新) | 项目名 + 状态徽章 + 文件上传（status=parsing 时） |
| `web-next/components/message-list.tsx` (新) | 渲染 `UIMessage.parts`（text / tool-XXX / dynamic-tool） |
| `web-next/components/composer.tsx` (新) | 自动调整高度 textarea + status 相关 quick replies + send/stop |
| `web-next/components/file-sidebar.tsx` (新) | 项目结构（主标 5 文件夹 / 陪标 / 解析概览 / 折叠切换） |
| `web-next/components/tools/parse-tool-result.tsx` (新) | parseTender 工具 UI：input-available 进度 / output-available 4 tab |
| `web-next/components/tools/parser-report.tsx` (新) | K01-K14 / 标记扫描 / 风险条款 / 结构化数据 4 tab |
| `web-next/components/tools/tool-fallback.tsx` (新) | 通用 JSON 工具渲染（match / generate / review / export 暂用 fallback） |
| `main.py` (修复) | LLM 流式 `text-delta` 必须用 `text-start`/`text-end` 包裹（AI SDK Protocol） |

### 验证

```bash
# 启动后端
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
# 启动前端
cd web-next && npm run dev

# 验证 SSE
curl -N -X POST http://localhost:8000/projects/1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"继续"}]}'
# → data: {"type":"tool-input-available", toolName:"matchMaterials", ...}
```

TypeScript 编译：`npx tsc --noEmit` → TYPECHECK_OK
浏览器：项目页 chat thread 加载 → 输入「继续」→ 看到 `matchMaterials` 工具调用 → JSON 渲染

### 后续待处理

- Stage 2.D：删除 `web/` 目录（destructive，需用户确认）
- 添加 match / generate / review / export 工具 UI（目前用 ToolFallback）
- 部署到 Vercel / Docker
