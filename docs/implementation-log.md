# QuickBid 实现日志

## 2026-06-18：Phase 2-3 — 终审、导出和业务可用性

### Phase 2 完成项

- `ReviewerAgent` 从固定 mock 改为 DeepSeek `chat_json()` 结构化审查，输出固定 `checks[] + summary` schema。
- LLM 不可用、缺少 `tender_id` 或缺少 `draft.md` 时，Reviewer 返回明确失败 schema，不再假装通过。
- `/chat` 的 `reviewTender` tool output 返回 `checks`、`summary`、`error`，前端可用 `ToolFallback` 直接展示。
- `POST /tenders/{tender_id}/export` 以 `tender.draft_path` 对应 `draft.md` 为输入，支持：
  - `format="word"` / `docx`：生成 `exports/tender_{tender_id}.docx`
  - `format="markdown"` / `md`：生成 `exports/tender_{tender_id}.md`
  - `format="pdf"`：明确返回不支持
- 新增 `/downloads/{tender_id}/{format}` 下载已导出文件。
- `/chat` 的「导出Word」会触发 Word 导出；导出失败通过 `exportTender` tool output 展示错误。
- 「自动修正」不再声称已自动 patch，MVP 阶段提示人工修改或指定章节重新生成。

### Phase 3 完成项

- Composer 快捷指令按项目状态收口：
  - `parsed` -> 继续
  - `outline_generating` -> 继续
  - `materials_preparing` -> 生成
  - `generated` -> 终审 / 导出Word
  - `reviewed` -> 导出Word
- Sidebar / Header 状态标签支持 `outline_generating`、`generating`、`generated`、`reviewed`。
- `MatchToolResult` 使用 `file_path` 判断材料匹配结果，避免把文件系统材料误判为无匹配。
- `GeneratorToolResult` 展示失败章节、占位章节和引用材料。
- 新增 `ExportToolResult`，展示导出成功路径、下载链接和 Word 导出失败错误。
- 材料库页面保留最小增强：来源文件描述、分类、字符数。

### 验证

```bash
.venv/bin/python -m py_compile models.py orchestrator.py main.py agents/*.py
PYTHONPATH=. .venv/bin/python tests/test_export_tender.py
PYTHONPATH=. .venv/bin/python tests/test_reviewer_agent.py
cd web-next && npx tsc --noEmit
```

## 2026-06-18：Phase 1 — 主标 MVP 闭环

### 完成项

- `GET /projects/{id}` 返回 `tenders` 和 `active_main_tender_id`，并兼容旧 `tender_id` 字段。
- 当前主标选择改为按最新 `Tender.id` 倒序，优先选择 `draft_path` 非空记录，避免重新生成后回退到旧 tender。
- `FileSidebar` 和 `MarkdownViewer` 使用 `active_main_tender_id ?? tender_id`，不再依赖硬编码 tender id。
- `/chat` 的「生成」走 Orchestrator 状态机主标生成路径，生成完成后项目状态为 `generated`。
- `MatcherAgent` 继续从 `materials/` 文件夹读取材料，匹配结果输出 `file_path`、`material_title`、`category`、`match_score`。
- `GeneratorAgent` 改为按 `file_path` 读取材料正文：`.md` 直接读文本，`.docx` 复用现有 DOCX 提取能力；数据库 `Material` 不再作为主标 MVP 生成主路径。
- 生成失败时通过 `errors` / `failed` / 章节 `error` 暴露给 `generateTender` tool output；缺少 LLM key 不再输出占位成功稿。
- `Orchestrator` 将主标落盘为 `main/cover.md`、`main/draft.md`、`main/deviation.md`、`main/<category>/<chapter>.md`。
- 右侧文件栏展示顶层文件和分类章节文件，点击后进入全屏 Markdown 查看器。

### 验证

```bash
.venv/bin/python -m py_compile models.py orchestrator.py main.py agents/*.py
PYTHONPATH=. .venv/bin/python tests/test_generator_material_files.py
PYTHONPATH=. .venv/bin/python tests/test_orchestrator_file_writing.py
PYTHONPATH=. .venv/bin/python tests/test_matcher_validation.py
cd web-next && npx tsc --noEmit
```

## 2026-06-16：主标 MVP 建设计划归档

当前阶段的产品与工程建设计划已归档到 `docs/main-bid-mvp-plan.md`，作为后续反复确认 Phase 0-5 范围、公共接口和验收标准的基准文档。

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


## 2026-06-16：Phase 4 — GeneratorAgent UI 组件 + 文件查看器 + 后端文件 API

### 新增组件

**GeneratorToolResult** (`web-next/components/tools/generator-tool-result.tsx`)
- 紧凑型工具结果卡片（主内容在右侧 FileSidebar）
- 三态：streaming（Loader2 进度条）/ error（红色 banner）/ complete（章节归档预览）
- 按 `category` 聚合章节文件（`groupByCategory` helper），显示 6 分类文件夹树
- 复制/下载全部 Markdown（`fullDraftMarkdown` 拼装函数）
- 完成态底部绿色 banner："→ 已归档到右侧项目文件面板"
- 错误态显示失败章节数量和前 3 条错误信息

**MarkdownViewer** (`web-next/components/markdown-viewer.tsx`)
- 全屏 Markdown 查看器（`absolute inset-0 z-20` 覆盖 chat 主区）
- 通过 `readTenderFile(projectId, tenderId, filePath)` API 拉取内容
- ReactMarkdown + remarkGfm 渲染（GFM 表格、删除线、任务列表）
- 顶栏：面包屑导航（项目 ID > 文件夹 > 文件名）+ 复制/下载/关闭按钮
- `prettyFolder` helper 去数字前缀："01_公司资质" → "公司资质"
- ESC 键关闭（`useEffect` keydown listener）
- 三态：loading（Loader2 spinner）/ error（ErrorState 红色卡片）/ content（prose 样式）
- 自定义 markdown 组件：h1-h4 分级标题、表格边框、代码块暖色背景、blockquote 左边框

### FileSidebar 动态化

**变更点** (`web-next/components/file-sidebar.tsx`)
- 删除 `MAIN_BID_FOLDERS` 硬编码常量
- 新增 `useEffect` 监听 `project.status`：`generating` / `generated` / `reviewed` 时拉文件树
- 调用 `listTenderFiles(projectId, tenderId)` 获取 `TenderFileTree`
- 新增 `DynamicFolderRow` 组件：显示动态文件夹 + 文件列表（可展开）
- 文件点击 → `router.push(/projects/${id}?file=${path})` 触发查看器路由
- `prettyCategory` helper 去数字前缀（同 MarkdownViewer）
- 陪标部分简化为"陪标文件（待实现）"占位
- 加载态：Loader2 spinner + "加载文件树…"
- 空态："暂无文件"

### 路由集成

**page.tsx** (`web-next/app/projects/[id]/page.tsx`)
- 接收 `searchParams.file` query 参数（Next.js 15 Promise API，用 `use()` 解包）
- 有 `file` → 渲染 `<MarkdownViewer>` 覆盖主区
- 无 `file` → 正常渲染 `<ChatThread>`
- `MarkdownViewerWrapper` 组件处理关闭逻辑：`window.history.pushState` 去除 query 参数
- Sidebar 永远显示（左右布局不变）

**message-list.tsx** (`web-next/components/message-list.tsx`)
- 新增 `toolName === "generateTender"` 分支路由到 `<GeneratorToolResult>`
- 导入 `GeneratorToolResult` 组件

### 后端文件 API

**main.py 新增两个端点**：

1. `GET /projects/{project_id}/tenders/{tender_id}/files` — 返回文件树
   - 遍历 `projects/{ts}_{name}/{type}/` 目录（如 `main/`）
   - 聚合文件夹（category 格式 `01_公司资质`）
   - 每个文件夹返回 `.md` 文件列表（提取章节编号 `01_xxx.md`）
   - 顶层文件（`draft.md`, `cover.md`）单独列出
   - 返回 `TenderFileTree` 结构

2. `GET /projects/{project_id}/tenders/{tender_id}/files/{file_path:path}` — 读取单文件内容
   - 路径安全检查：`resolve()` + `relative_to()` 防止 `../` 越权
   - 返回 Markdown 原始文本（`Content-Type: text/plain; charset=utf-8`）

### Orchestrator 文件落盘

**已有实现** (`orchestrator.py:587-698`)
- `_write_main_tender_files()` 方法在 `_start_generation()` 中被调用
- 落盘结构：
  ```
  main/
    cover.md              # 封面+目录
    draft.md              # 完整拼装 Markdown
    deviation.md          # 偏离表占位
    01_公司资质/          # 随 outline 动态生成
      01_营业执照与法人证明.md
      02_资质证书.md
    02_业绩案例/
      ...
    03_技术方案/
    04_实施方案/
    05_商务文件/
    06_其他/
  ```
- 文件名 sanitize：`_sanitize_filename()` 替换非法字符 + 截断到 50 字符
- 落库：`tender.draft_path = str(draft_path)` + commit
- 修复：添加 `import logging` + `logger = logging.getLogger(__name__)`

### API 扩展

**lib/api.ts** 新增两个 API：
- `listTenderFiles(projectId, tenderId)` → `TenderFileTree`（文件夹树 + 文件列表）
- `readTenderFile(projectId, tenderId, filePath)` → `string`（Markdown 原始内容）

### 类型定义

```typescript
interface TenderFileEntry {
  name: string; path: string; size: number;
  chapter_no?: number; kind?: string;
}
interface TenderFolder {
  name: string; category: string; category_no: string;
  path: string; files: TenderFileEntry[];
}
interface TenderFileTree {
  tender_id: number; type: string; root: string;
  folders: TenderFolder[]; top_files: TenderFileEntry[];
}
```

### 验证

- TypeScript 编译通过：`npx tsc --noEmit` → EXIT=0
- Python imports 通过：`from orchestrator import Orchestrator` ✓、`from main import app` ✓
- **后端 API 冒烟测试**：
  - `GET /projects` → 返回项目列表 ✓
  - `GET /projects/7` → 返回 `tender_id: 5` ✓
  - `GET /projects/7/tenders/5/files` → 返回文件树（6 分类 + 文件列表）✓
  - `GET /projects/7/tenders/5/files/01_公司资质/01_公司资质.md` → 返回 Markdown 内容 ✓
- **前端服务启动**：
  - Backend: `http://localhost:8000` ✓
  - Frontend: `http://localhost:3000` ✓
  - Title: "QuickBid — 标书工作台" ✓

### 已知限制

- GeneratorAgent 依赖 `TENDER_DEEPSEEK_API_KEY`；缺少 LLM key 时生成会明确失败，不再输出占位成功稿。
- 陪标文件树未实现（FileSidebar 仅占位）

### UI 冒烟测试清单（需手动验证）

**前提**：启动后端 + 前端，浏览器打开 `http://localhost:3000`

1. **项目列表页** (`/projects`)
   - [ ] 显示项目列表
   - [ ] 点击项目进入 chat 页面

2. **Chat 页面** (`/projects/7`)
   - [ ] 左侧 Sidebar 显示「QuickBid」logo + 项目列表
   - [ ] 顶部 ChatHeader 显示项目名「测试材料匹配」+ 状态徽章「generating」
   - [ ] 右侧 FileSidebar 显示：
     - [ ] 「招标文件」卡片
     - [ ] 「解析概览」卡片（显示 K01/K02/K04）
     - [ ] 「主标」文件树（6 分类文件夹可展开）
   - [ ] 点击「01_公司资质」文件夹 → 展开显示「01_公司资质.md」

3. **文件查看器** (`/projects/7?file=01_公司资质/01_公司资质.md`)
   - [ ] 全屏覆盖 chat 主区
   - [ ] 顶栏面包屑：「P007 > 公司资质 > 01_公司资质.md」
   - [ ] Markdown 正确渲染（标题、列表、段落）
   - [ ] 「复制」按钮点击 → 显示「已复制」✓
   - [ ] 「下载」按钮点击 → 下载 .md 文件
   - [ ] 「关闭」按钮点击 → 回到 chat 页面
   - [ ] ESC 键 → 关闭查看器

4. **Chat 工具调用**（需后端 GeneratorAgent 实现后测试）
   - [ ] 输入「生成」→ SSE 流式输出
   - [ ] GeneratorToolResult 卡片显示章节归档预览
   - [ ] 底部绿色 banner「→ 已归档到右侧项目文件面板」
   - [ ] 右侧 FileSidebar 自动刷新文件树

### 后续待处理

- **GeneratorAgent 完整实现**（逐章 LLM 调用 + 内容拼装）——当前是 stub
- **UI 手动测试**（上述清单）
- 偏离表生成（DeviationAgent）
- 陪标支持
