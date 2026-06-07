# QuickBid 标书制作工具 — 技术设计文档

> 本文档记录 QuickBid 的核心架构与设计决策。
> v3 多 Agent 架构详见 [multi-agent-architecture.md](./multi-agent-architecture.md)
> 实现日志详见 [implementation-log.md](./implementation-log.md)

---

## 一、核心范式：确认驱动对话

### 1.1 核心理念

> **不做意图识别。只做状态路由 + 句式匹配。**
> AI 做一步 → 用户确认/纠正 → 继续。

```
用户输入 → 根据当前状态（step）分发给固定 handler
          → handler 用正则/关键词匹配少量关键句式
          → AI / Agent 完成本步骤工作
          → 返回结果，等待用户确认/纠正/继续
```

### 1.2 三句黄金法则

| 句式 | 含义 |
|------|------|
| `继续` / `确认` / `好的` | 接受当前结果，进入下一步 |
| `修改` / `换 xxx` | 指出问题，AI 原地修正 |
| `自动修正` | 批量应用预设修正规则 |

---

## 二、系统架构

### 2.1 组件关系

```
用户（CLI / Web 浏览器）
  │
  ├── CLI 入口 ──→ cli.py（交互层）
  │                   │
  ├── Web 入口 ──→ main.py（FastAPI REST API）
  │                   │
  │              ┌────┴────┐
  │              ▼         ▼
  │       orchestrator.py   ←── Agent 编排器（状态机 + Agent 调度）
  │              │
  │    ┌─────────┼─────────┬─────────┬──────────┐
  │    ▼         ▼         ▼         ▼          ▼
  │  Parser   Matcher  Generator Reviewer  SubBid
  │  Agent    Agent    Agent     Agent     Agent
  │              │
  │              ▼
  │       models.py ←── SQLAlchemy ORM + SQLite
  │
  ├── file_utils.py      ← PDF/DOCX 文本提取
  └── export_engine.py   ← Word/PDF 导出
```

### 2.2 组件职责

| 文件 | 职责 |
|------|------|
| `cli.py` | CLI 交互层，接收用户输入 → 调用 Orchestrator |
| `main.py` | FastAPI REST API，接收 HTTP 请求 → 调用 Orchestrator |
| `orchestrator.py` | Agent 编排器，状态机 + Agent 调度 + 上下文管理 |
| `agents/` | 5 个特化 Agent（Parser / Matcher / Generator / Reviewer / SubBid） |
| `models.py` | SQLAlchemy 数据模型 + SQLite 数据库初始化 |
| `config.yaml` | 全局配置（路径 / AI provider / 分类定义） |
| `file_utils.py` | PDF/DOCX 文件文本提取 |
| `export_engine.py` | Word/PDF/Markdown 导出 |
| `web/` | Vue.js 3 前端（Element Plus） |

---

## 三、数据模型

### 3.1 实体关系

```
Project（投标项目）
  │
  ├── Tender（主标/陪标）
  │     ├── draft_path
  │     ├── deviation_path
  │     └── review_report_path
  │
  └── MaterialUsage（材料使用记录）
        └── Material（材料库材料）
```

### 3.2 核心模型

#### Project
- `id` / `name` / `tender_file_path`
- `status`: `parsing` → `parsed` → `materials_preparing` → `generating` → `done`
- `parsed_data`: 完整 K01-K14 JSON（`json.dumps` 序列化）
- `project_name` / `tender_no` / `budget` / `deadline` / `open_time`（解析出的字段）

#### Tender
- `project_id` (FK) / `type` (`"main"` \| `"sub"`) / `status` (`"draft"` \| `"reviewing"` \| `"finalized"`)
- `draft_path` / `deviation_path` / `review_report_path`

#### Material
- `title` / `category`（01-06） / `tags` / `description`
- `content` (Markdown) / `content_type` / `char_count`
- `ai_summary` / `version` / `is_deleted` / `source_file`

---

## 四、工作流状态机

### 4.1 状态流转

```
IDLE → AWAIT_TENDER_FILE → PARSING → AWAIT_PARSE_CONFIRM
                                          │
                                          ▼
                                 AWAIT_OUTLINE_CONFIRM   ← 新增
                                          │
                                          ▼
                                 AWAIT_CHAPTER_CONFIRM
                                          │
                                          ▼
                                 GENERATING_DRAFT
                                          │
                                          ▼
                                 AWAIT_DRAFT_CONFIRM
                                          │
                                          ▼
                                 AWAIT_REVIEW_ACTION
                                          │
                                          ▼
                                 AWAIT_EXPORT_CONFIRM → DONE
```

### 4.2 各状态 + Agent 映射

| 状态 | Agent | 关键句式 |
|------|-------|---------|
| `IDLE` | — | `新建项目：xxx` |
| `AWAIT_TENDER_FILE` | — | `放好了` |
| `PARSING` | **ParserAgent** | 自动执行 |
| `AWAIT_PARSE_CONFIRM` | **MatcherAgent.generate_outline** | `继续` / `预算应该是900万` |
| `AWAIT_OUTLINE_CONFIRM` | **（用户交互）** | `继续` / `删除第N章` / `加一章 [标题]` / `改 [旧] 为 [新]` / `重排` |
| `AWAIT_CHAPTER_CONFIRM` | **MatcherAgent.match_materials** | `继续` / `换第三章` |
| `GENERATING_DRAFT` | **GeneratorAgent** | 自动执行 |
| `AWAIT_DRAFT_CONFIRM` | **ReviewerAgent** | `终审` / `修改` |
| `AWAIT_REVIEW_ACTION` | — | `自动修正` / `导出Word` |

陪标额外流程：
```
AWAIT_DRAFT_CONFIRM → 用户说「生成陪标」
  → SubBidAgent 生成 → ReviewerAgent 审查（最多 2 次重试）
  → AWAIT_REVIEW_ACTION
```

### 4.3 会话持久化

每次状态转换后保存到 `.session.json`，支持跨 session 恢复。结构：
```json
{
  "current_project_id": 1,
  "step": "await_parse_confirm",
  "context": { "parsed_data": { ... }, "chapters": [ ... ] }
}
```

---

## 五、核心算法

### 5.1 招标文件解析（K01-K14）

由 **ParserAgent** 执行（详见 multi-agent-architecture.md）。

K01-K14 字段：项目名称 / 招标编号 / 招标人 / 预算金额 / 投标截止 / 开标时间 / 评分标准 / 技术要求 / 商务资质要求 / 星标项 / 废标条款 / 章节要求 / 偏离表格式 / 演示要求

### 5.2 材料匹配

由 **MatcherAgent** 执行：关键词过滤 → 语义相似度排序 → 返回每个章节 Top-N 推荐。

### 5.3 终审检查（C01-C10）

由 **ReviewerAgent** 执行，主标和陪标都须经审查。

C01-C10：名称一致性 / 产品名称 / 时间一致性 / 期限一致性 / 金额一致性 / 人员一致性 / 章节完整性 / 星标项覆盖 / 废标条款自查 / 资质引用有效性

---

## 六、目录结构

```
Quickbid/
├── config.yaml                  # 全局配置
├── requirements.txt             # Python 依赖
├── README.md                    # 项目概述
├── models.py                    # SQLAlchemy 数据模型
├── cli.py                       # CLI 交互入口
├── main.py                      # FastAPI REST API
├── orchestrator.py              # Agent 编排器（v3）
├── file_utils.py                # PDF/DOCX 文本提取
├── export_engine.py             # Word/PDF 导出
├── agents/                      # 多 Agent 包（v3）
│   ├── __init__.py
│   ├── base.py                  # BaseAgent + AgentContext
│   ├── parser_agent.py
│   ├── matcher_agent.py
│   ├── generator_agent.py
│   ├── reviewer_agent.py
│   └── subbid_agent.py
├── scripts/
│   └── import_materials.py
├── docs/
│   ├── technical-design.md      # 本文档
│   ├── multi-agent-architecture.md
│   ├── architecture-decisions.md
│   └── implementation-log.md
├── materials/                   # 材料库（永久积累）
│   ├── 01_公司资质/
│   ├── 02_业绩案例/
│   ├── 03_技术方案/
│   ├── 04_实施方案/
│   ├── 05_商务文件/
│   └── 06_其他/
├── projects/                    # 项目目录
├── exports/                     # 导出目录
└── web/                         # Vue.js 3 前端
    ├── src/
    │   ├── api/index.ts
    │   ├── router/index.ts
    │   ├── store/project.ts
    │   ├── views/project/
    │   └── views/material/
    └── ...
```

---

## 七、技术选型

| 用途 | 选型 | 原因 |
|------|------|------|
| 对话管理 | 纯 Python（无 LangChain） | 状态机逻辑简单，不需引入框架 |
| 多 Agent 编排 | 自建 Orchestrator | 轻量可控，Agent 间通过结构化上下文通信 |
| 数据库 | SQLite + SQLAlchemy | 本地持久化，无需服务 |
| API 层 | FastAPI | 供 Web 前端集成 |
| Web 前端 | Vue 3 + Element Plus + Vite | 企业级 UI，TypeScript |
| PDF 解析 | PyMuPDF | 速度快、文本提取准 |
| Word 导出 | python-docx | 成熟稳定 |
| PDF 导出 | WeasyPrint | Python 原生方案 |
| AI | DeepSeek API (OpenAI 兼容) | 成本低、中文理解强 |
| LLM 客户端 | openai SDK | DeepSeek 兼容 OpenAI API 格式 |

---

## 八、设计原则与教训

### 8.1 设计原则

1. **固定路径，不传递路径参数** — 文件路径由系统生成并存在 DB
2. **每个状态只处理本状态的事** — Handler 之间无交叉依赖
3. **会话持久化做到最细粒度** — 每步操作后立即保存
4. **AI 做一步，用户确认一步** — 不在用户确认前做不可逆操作
5. **Agent 无状态** — 所有上下文由 Orchestrator 的 AgentContext 管理
6. **所有标书产出必经审查** — 主标和陪标都须通过 ReviewerAgent

### 8.2 已踩过的坑

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| SQLAlchemy 2.0 `DeclarativeBase()` 直接实例化 | 需显式继承 | `class Base(DeclarativeBase)` |
| WorkflowStep 用 Enum 比较恒为 False | Enum 不是 str 子类 | 用 `class WorkflowStep(str)` |
| CLI stdin pipe 导致 EOFError | `input()` 在 pipe 模式遇 EOF | 测试脚本直接调用 `handle()` |
| `str(dict)` 非有效 JSON | Python repr ≠ JSON | 用 `json.dumps(..., ensure_ascii=False)` |
| PyQt5 GUI 与 CLI 数据模型不兼容 | 两套并行架构 | 移除 PyQt5，统一到 SQLAlchemy 模型 |

---

## 九、当前状态与 TODO

### 已完成
- ✅ 状态机（cli.py，9 状态完整工作流）
- ✅ SQLAlchemy 数据模型（Project / Tender / Material / MaterialUsage）
- ✅ FastAPI REST API（11 个端点）
- ✅ 会话持久化（.session.json）
- ✅ Vue.js Web 前端骨架（路由 / 7 步向导 / 材料管理）
- ✅ 目录结构搭建（materials / projects / exports + .gitkeep）
- ✅ PyQt5 冗余代码清理

### 进行中 / 待实现

| 优先级 | 功能 | 状态 |
|--------|------|------|
| P0 | 多 Agent 框架（agents/ + orchestrator.py） | 待实现 |
| P0 | ParserAgent + DeepSeek K01-K14 解析 | 待实现 |
| P0 | GeneratorAgent + 标书初稿生成 | 待实现 |
| P1 | MatcherAgent + 材料匹配 | 待实现 |
| P1 | ReviewerAgent + C01-C10 审查 | 待实现 |
| P1 | 陪标模式（SubBidAgent + Reviewer 审查） | 待实现 |
| P1 | 材料库批量导入脚本 | 待实现 |
| P2 | Word 导出（目录/页眉页脚） | 待实现 |
| P2 | PDF 导出（WeasyPrint） | 待实现 |
| P3 | Web 前端完善（认证/错误处理/空状态） | 部分完成 |

---

*最后更新：2026-05-30 | License: MIT*
