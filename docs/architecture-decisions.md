# Architecture Decision Records (ADR)

记录 QuickBid 项目的关键架构决策。每个 ADR 包含：状态、上下文、决策、后果。

---

## ADR-001：前端从 Vue 3 + Element Plus 迁移到 Next.js 15 + Vercel AI SDK

- **状态**：已采纳（2026-06-03）
- **背景**：旧 `web/` 是 Vue 3 + Element Plus + Vite 的单页应用，存在以下问题：
  1. 解析时 65 秒黑屏，仅 `el-steps` 静态进度条，token 不到前端无可观测性
  2. 解析报告 4 个 tab 在 `ParserResultPanel.vue`（519 行单文件）复用 Element Plus 表格，K01-K14 退化为 chat cards
  3. `ChatView.vue` 633 行把 chat、sidebar、upload、parser 面板、状态机全塞一起
  4. 关键词路由靠 `handleSend` 字符串匹配，脆弱
- **决策**：新建 `web-next/` 目录，迁移到 Next.js 15 + React 19 + Tailwind 4 + Vercel AI SDK
  - **后端 SSE**：用 `sse-starlette` + OpenAI SDK `stream=True` 实现 [Vercel AI SDK Data Stream Protocol](https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#data-stream-protocol)；事件序列：`start` → `text-start`/`text-delta`/`text-end` → `tool-input-available` → `tool-output-available` → `finish-step` → `finish-message` → `finish`
  - **前端 chat**：`@ai-sdk/react` 的 `useChat` + `DefaultChatTransport({ api: '/api/projects/{id}/chat' })`；自动把 SSE 解析成 `UIMessage.parts`（text / tool-XXX / dynamic-tool）
  - **状态机**：保留关键词路由（不重做）；后端 `main.py:_run_chat_sse` 路由：放好了→parse，继续→match，生成→generate，终审→review，导出→export
  - **API 代理**：`next.config.ts` 的 `rewrites` 把 `/api/*` 转发到 FastAPI `:8000`
  - **设计 tokens**：Tailwind 4 `@theme inline` 直接用 CSS 变量（暖色编辑风格，移植自旧 `web/src/style.css`）
  - **assistant-ui**：作为 UI 框架之一安装但暂不直接用，工具渲染自写（`components/quickbid/tools/*.tsx`）
- **后果**：
  - 用户看到 LLM 逐 token 流式输出（`text-delta`），不再黑屏
  - 解析报告 4 tab 用纯 React 组件实现，K01-K14 字段结构化展示，模块化数据真实呈现
  - `useChat` 自动处理 reconnect/重试/abort；不必手写 fetch + ReadableStream
  - 迁移期间保留 `web/` 作回退，迁移完成删除
  - 增加新依赖：Next.js 15 / React 19 / @ai-sdk/react 3.x / ai 6.x / lucide-react / sse-starlette

## 决策摘要表

| ADR | 决策 | 状态 |
|---|---|---|
| ADR-001 | 前端从 Vue 3 迁移到 Next.js 15 + Vercel AI SDK | 已采纳 |
