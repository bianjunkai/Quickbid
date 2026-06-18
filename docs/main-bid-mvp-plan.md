# QuickBid 主标/陪标 MVP 建设计划

> 本文记录当前阶段的产品与工程建设计划，用于后续反复确认范围、优先级和验收标准。近期目标是先交付业务同事可用的主标 + 陪标 MVP，不在本阶段阻塞 PDF、权限、部署等产品化能力。

## 目标

QuickBid 当前建设重点是收口主标和陪标链路：

上传招标文件 -> 解析 -> 确认/修改提纲 -> 匹配材料 -> 生成主标 -> 文件栏查看 -> 终审 -> 生成陪标 -> 陪标终审 -> Word 导出。

默认策略：

- DeepSeek 继续作为默认模型，不引入混合模型路由。
- `materials/` 文件夹是 MVP 阶段的材料权威来源。
- 数据库 `Material` 后续可作为同步增强，不作为主标 MVP 的主路径。
- Word 是正式交付格式；Markdown 是中间产物和调试格式。
- 真实招标文件、生成结果和材料内容均按敏感数据处理，不进入 Git。

## Phase 0：收口技术债和状态漂移

- 清理 `main.py` 中重复定义的文件树/文件读取端点，只保留一套安全实现。
- 修复 `/projects/{id}/chat` 中状态机分支提前 `return` 导致“生成/终审/导出”显式分支不可达的问题。
- 将 `review/2026-06-15_orchestrator-review.md` 中已完成项标记完成，保留未完成项。
- 更新过期文档：`technical-design.md`、`CLAUDE.md`、`web-next/README.md`，把 Vue/“Agent 待实现”等旧描述改为当前 Next.js + Agent 状态。
- 保持 6 个材料分类不变：`01_公司资质` 到 `06_其他`。
- 恢复 `materials/04_实施方案/.gitkeep`，避免空目录从工作树消失，破坏 6 分类约定。
- 清理提交边界：移除 `.DS_Store` 这类本地二进制元数据，并确保新增文件进入同一变更集，包括 `docs/main-bid-mvp-plan.md`、`web-next/components/markdown-viewer.tsx`、`web-next/components/tools/generator-tool-result.tsx`。
- 收口 Orchestrator 文件落盘 review 问题：
  - `_write_main_tender_files` 对非数字章节号做容错，避免 `int(no)` 触发 `ValueError` 后整次落盘失败。
  - 将 `_sanitize_filename` 的正则改成更清晰的写法，并补一个覆盖 `r`、`n`、`t` 字母和换行/制表控制字符的快速断言。
  - 删除 `run_workflow` 中不再使用的 `draft_content` 局部变量。
  - 删除 `_write_main_tender_files` 中未使用的 `outline` 局部变量，移除函数内重复 `logging` / `re` 导入。

## Phase 1：主标 MVP 闭环

状态（2026-06-18）：已完成主标 MVP 闭环的工程项，包括 active tender 绑定、材料 `file_path` 主路径、主标文件落盘和前端文件查看。

### 后端项目详情

`GET /projects/{id}` 返回当前主标信息：

- `tenders: [{ id, type, status, draft_path, created_at }]`
- `active_main_tender_id`

选择当前主标时必须确定性地返回最新可查看记录：

- 按 `Tender.id` 或 `created_at` 倒序选择最新 `type="main"` 的 tender。
- 文件查看使用的 active tender 优先要求 `draft_path` 非空。
- 多次重新生成后，侧边栏和 Markdown 查看器不能回退到旧 tender。

### 前端 tender 绑定

- 移除所有 `tenderId=1` 硬编码。
- `FileSidebar` 和 `MarkdownViewer` 均使用 `active_main_tender_id`。

### 项目状态

统一使用以下状态：

- `parsing`
- `parsed`
- `outline_generating`
- `materials_preparing`
- `generating`
- `generated`
- `reviewing`
- `reviewed`
- `done`

生成完成后使用 `generated`，不要继续停留在 `generating`。

### 材料匹配

- `MatcherAgent` 继续从 `materials/` 文件夹匹配。
- 匹配结果输出 `file_path`、`material_title`、`category`、`match_score`。

### 主标生成

`GeneratorAgent` 以 `file_path` 为主读取材料正文：

- `.md` 直接读取文本。
- `.docx` 使用现有 DOCX 提取能力；如果不可用，再明确补依赖。
- 数据库 `Material` 只作为后续同步增强，不作为 MVP 主路径。
- 如果 `BidLLMClient` 不可用或缺少 `TENDER_DEEPSEEK_API_KEY`，生成必须作为失败返回，不能把 `[待补充]` 占位章节当作成功稿件。
- 章节级失败必须写入 `errors` / `chapter_error`，并通过 `generateTender` tool output 暴露给前端。
- 前端生成卡片需要能区分成功章节、失败章节和占位章节。

`Orchestrator` 生成主标后写入：

- `main/cover.md`
- `main/draft.md`
- `main/deviation.md`
- `main/<category>/<chapter>.md`

前端右侧文件栏展示顶层文件和分类章节文件，点击后全屏 Markdown 查看。

## Phase 2：终审和 Word 导出

状态（2026-06-18）：已完成 MVP 终审 schema、Markdown/Word 导出和下载接口；PDF 继续后置。

### 终审

`ReviewerAgent` 从 mock 改为 DeepSeek 结构化审查，输出固定 schema：

```json
{
  "checks": [
    {
      "check_id": "string",
      "check_name": "string",
      "status": "pass | warning | fail",
      "issue": "string",
      "suggestion": "string"
    }
  ],
  "summary": {
    "high": 0,
    "medium": 0,
    "low": 0
  }
}
```

- `/chat` 对“终审”返回 `reviewTender` tool event。
- 前端先用 `ToolFallback` 展示，后续再做专用 UI。
- `自动修正` 暂不做复杂 patch；MVP 中只允许按审查建议重新生成指定章节或提示人工修改。

### Word 导出

- 输入以 `tender.draft_path` 对应的 `draft.md` 为准。
- 使用 `python-docx` 生成 `.docx`。
- 输出到 `exports/tender_{tender_id}.docx`。
- `POST /tenders/{id}/export` 返回 `{ format, export_path, download_url }`。
- Markdown 导出保留为调试/兜底；PDF 后置。

## Phase 3：业务可用性增强

状态（2026-06-18）：已完成 MVP 错误态和状态快捷指令收口；更复杂的专用审查 UI、章节级重生成交互和材料库 CRUD 后置。

- 前端补齐业务同事需要的错误态：
  - 未上传文件
  - 解析失败
  - 无材料匹配
  - 某章节生成失败
  - Word 导出失败
- 生成卡片展示失败章节、占位章节和引用材料。
- Composer 快捷指令按项目状态精简：
  - `parsed` -> 继续生成提纲
  - `outline_generating` -> 继续匹配材料
  - `materials_preparing` -> 继续生成主标
  - `generated` -> 终审 / 生成陪标 / 导出Word
  - `reviewed` -> 生成陪标 / 导出Word
- 添加材料库管理最小增强：显示文件来源、分类、字符数，不在 MVP 内强制做数据库同步。

## Phase 4：陪标和偏离表

状态（2026-06-18）：已完成陪标 MVP 闭环，包括 DeepSeek 生成、独立 `Tender(type="sub")` 落盘、主/陪标文件栏分组、偏离表生成和 Reviewer 审查重试。

- `SubBidAgent` 接入 DeepSeek，基于主标、招标事实和商务资质生成陪标。
- 陪标落盘到 `sub/`，使用独立 `Tender(type="sub")`。
- `FileSidebar` 支持主标/陪标分组展示。
- Orchestrator 生成商务/技术偏离表，替换当前 `deviation.md` 占位。
- 陪标必须经过 Reviewer 审查，失败时最多重试 2 次；重试后仍失败则保留 `review_failed` tender 状态，不把项目强行标为完成。

## Phase 5：产品化前准备

- 增加项目归档、删除项目时清理关联运行时文件的策略。
- 梳理敏感数据边界：`.env`、`projects/`、`exports/`、真实材料和真实招标文件均不提交。
- 如果后续从“业务同事内部工具”升级为产品化，再新增认证、权限、部署、审计日志；当前计划不纳入 MVP。

## 公共接口

### ProjectDetail

新增字段：

```ts
type ProjectDetail = {
  tenders: TenderSummary[]
  active_main_tender_id?: number
}
```

### TenderSummary

```ts
type TenderSummary = {
  id: number
  type: "main" | "sub"
  status: string
  draft_path?: string
  created_at: string
}
```

### TenderFileTree

保持：

- `tender_id`
- `type`
- `root`
- `folders`
- `top_files`

### SSE tool events

`/projects/{id}/chat` 必须稳定 emit AI SDK Data Stream Protocol：

- `parseTender`
- `outlineDesign`
- `matchMaterials`
- `generateTender`
- `reviewTender`
- `exportTender`

### 文件与导出接口

- `/projects/{project_id}/tenders/{tender_id}/files` 和 `/files/{path}` 只保留一套实现，且校验 tender 属于 project。
- `/tenders/{tender_id}/export` MVP 支持 `format="word"` 和 `format="markdown"`。
- PDF 先返回不支持或后置。

## 验收计划

### Python 快速检查

```bash
python3 -m py_compile models.py orchestrator.py main.py agents/*.py
PYTHONPATH=. python3 tests/test_matcher_validation.py
python3 -c "from models import init_db; init_db(); print('OK')"
```

### TypeScript 检查

```bash
cd web-next && npx tsc --noEmit
```

### API 冒烟

- 创建项目、上传文件、解析 SSE、继续生成提纲、继续匹配、继续生成主标。
- 校验 `active_main_tender_id` 非空。
- 校验文件树能列出 `cover.md`、`draft.md`、`deviation.md` 和章节文件。
- 校验 `MarkdownViewer` 能读取章节文件。
- 校验 Word 导出返回 `.docx` 路径且文件存在。

### 真实样例验收

- 使用一份脱敏医院信息化招标文件。
- 业务同事能在浏览器中完成主标生成和 Word 导出。
- 生成失败时能看到明确错误，不需要看终端日志。
