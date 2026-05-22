# QuickBid 标书制作工具 — 技术设计文档

> 本文档记录 QuickBid v2（确认驱动工作流）的核心架构与设计决策。

---

## 一、核心范式：从「意图识别」到「确认驱动」

### 1.1 传统实现的问题

传统 AI + 投标工具依赖**意图识别（Intent Detection）**：

```
用户输入 → LLM 判断意图 → 调用对应 Handler → 返回结果
```

痛点：
- 投标场景词汇多变（"开始"、"新建"、"启动"、"搞起来"……），意图识别容易漂移
- 每个新功能都需要重新训练/调优意图分类器
- 错误意图导致工作流中断，用户体验差

### 1.2 确认驱动的核心逻辑

> **不做意图识别。只做状态路由 + 句式匹配。**

```
用户输入 → 根据当前状态（step）分发给固定 handler
          → handler 用正则/关键词匹配少量关键句式
          → AI 在每个状态内部完成本步骤工作
          → 返回结果，等待用户确认/纠正/继续
```

**三句黄金法则：**

| 句式 | 含义 |
|------|------|
| `继续` / `确认` / `好的` | 接受当前结果，进入下一步 |
| `修改` / `换 xxx` | 指出问题，AI 原地修正 |
| `自动修正` | 批量应用预设修正规则 |

系统不猜用户想做什么——**用户告诉系统做什么，系统照做并确认**。

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                         用户                                 │
│            （飞书 / Telegram / CLI / 浏览器）                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ 对话 / REST API
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                      cli.py                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Conversation │  │ WorkflowStep │  │  会话持久化   │     │
│  │  Manager     │  │   状态机      │  │ .session.json│     │
│  └──────┬───────┘  └──────────────┘  └──────────────┘     │
│         │                                                  │
│         ▼                                                  │
│  ┌──────────────────────────────────────────────────┐     │
│  │              步骤处理器（按状态分发）                 │     │
│  │  _handle_idle / _handle_await_tender_file          │     │
│  │  _handle_await_parse_confirm / _handle_chapter_...  │     │
│  └──────────────────────────────────────────────────┘     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     models.py                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Project  │  │  Tender   │  │ Material │  │MaterialUs│   │
│  │ (投标项目)│  │  (标书)  │  │ (材料库) │  │  age     │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                        │                                     │
│                        ▼                                     │
│                  SQLite (tender.db)                          │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    main.py (FastAPI)                         │
│  对外 REST API，供前端/第三方集成调用                          │
└─────────────────────────────────────────────────────────────┘
```

### 组件职责

| 文件 | 职责 |
|------|------|
| `cli.py` | 对话管理器、状态路由、句式匹配、AI 调用（TODO） |
| `models.py` | SQLAlchemy 数据模型、数据库初始化 |
| `main.py` | FastAPI REST API（非必须，供前端集成） |
| `config.yaml` | 全局配置（路径、AI provider） |

---

## 三、数据模型

### 3.1 实体关系

```
Project (一个投标项目)
  │
  ├── Tender (一份标书，主标或陪标)
  │     ├── draft_path        # 初稿文件路径
  │     ├── deviation_path    # 偏离表路径
  │     └── review_report_path # 终审报告路径
  │
  └── MaterialUsage (材料使用记录)
        └── Material (材料库中的材料)
```

### 3.2 核心模型

#### Project（投标项目）

```python
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int]
    name: Mapped[str]                    # 项目名称（用户输入）
    tender_file_path: Mapped[str]       # 招标文件固定路径
    status: Mapped[str]                 # parsing / parsed /
                                         # materials_preparing / generating / done

    # 解析出的关键信息（JSON 存 parsed_data）
    project_name: Mapped[Optional[str]]  # K01
    tender_no: Mapped[Optional[str]]    # K02
    budget: Mapped[Optional[float]]      # K04
    deadline: Mapped[Optional[datetime]]# K05
    open_time: Mapped[Optional[datetime]]# K06
    parsed_data: Mapped[Optional[str]]  # 完整 K01-K14 JSON
```

#### Tender（标书）

```python
class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int]
    project_id: Mapped[int]              # 外键 → Project
    type: Mapped[str]                    # "main" | "sub"
    status: Mapped[str]                 # draft / reviewing / finalized

    draft_path: Mapped[Optional[str]]
    deviation_path: Mapped[Optional[str]]
    review_report_path: Mapped[Optional[str]]
```

#### Material（材料库）

```python
class Material(Base):
    __tablename__ = "materials"

    id: Mapped[int]
    title: Mapped[str]
    category: Mapped[str]               # 01_公司资质 / 02_业绩案例 / ...
    tags: Mapped[Optional[str]]        # JSON 数组
    description: Mapped[str]            # AI 生成摘要
    content: Mapped[str]                # Markdown 原文
    content_type: Mapped[str]           # "markdown" / "docx" / "pdf"
    char_count: Mapped[int]
    ai_summary: Mapped[Optional[str]]
    version: Mapped[int]               # 版本号
    is_deleted: Mapped[bool]
```

---

## 四、工作流状态机

### 4.1 状态定义

```
WorkflowStep
─────────────────────────────────────────────────────────►
IDLE → AWAIT_TENDER_FILE → PARSING → AWAIT_PARSE_CONFIRM
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

### 4.2 各状态 Handler

| 状态 | 入口触发 | 关键句式 | 出口动作 |
|------|---------|---------|---------|
| `IDLE` | 任意输入 | `新建项目：xxx` / `继续` / `当前项目` | `_create_project` |
| `AWAIT_TENDER_FILE` | 文件放置后 | `放好了` / `好了` | `_do_parse` |
| `AWAIT_PARSE_CONFIRM` | 解析完成 | `继续` / `预算900万` | `_handle_await_parse_confirm` |
| `AWAIT_CHAPTER_CONFIRM` | 材料匹配完成 | `继续` / `换第三章` | `_start_generation` |
| `AWAIT_DRAFT_CONFIRM` | 初稿生成 | `终审` / `修改` | `_run_review` |
| `AWAIT_REVIEW_ACTION` | 终审完成 | `自动修正` / `导出Word` | `_do_export` |

### 4.3 关键设计：会话持久化

每次状态转换后，将当前会话写入 `.session.json`：

```json
{
  "current_project_id": 1,
  "current_tender_id": null,
  "current_tender_type": null,
  "step": "await_parse_confirm",
  "context": {
    "parsed_data": { ... },
    "chapters": [ ... ]
  }
}
```

用户下次说「继续」时，系统根据 `step` 恢复工作流。

---

## 五、核心算法

### 5.1 招标文件解析（TODO: DeepSeek API）

```
输入：tender.pdf / tender.docx
输出：K01-K14 结构化信息

步骤：
1. 用 PyMuPDF 提取 PDF 文本（或 python-docx 解析 DOCX）
2. 构建 Prompt：要求 AI 按 K01-K14 格式输出关键信息
3. 调用 DeepSeek API（deepseek-chat）
4. 解析 JSON 结果，存入 Project.parsed_data
5. 返回给用户确认
```

**K01-K14 字段定义：**

| 字段 | 内容 |
|------|------|
| K01 | 项目名称 |
| K02 | 招标编号 |
| K03 | 招标人 |
| K04 | 预算金额 |
| K05 | 投标截止时间 |
| K06 | 开标时间 |
| K07 | 评分标准 |
| K08 | 技术要求 |
| K09 | 商务资质要求 |
| K10 | 星标项（必须响应） |
| K11 | 废标条款 |
| K12 | 章节模板要求 |
| K13 | 偏离表格式要求 |
| K14 | 演示要求 |

### 5.2 材料匹配

```
输入：K01-K14 + 材料库
输出：每章节 → 推荐材料

步骤：
1. 读取招标文件中章节要求（K12）
2. 按分类遍历材料库（01-06）
3. 对每个材料计算「招标文件关键词匹配度」
4. 返回每章节 Top-N 推荐 + 理由
5. 用户确认 / 替换 / 跳过
```

### 5.3 终审检查清单（C01-C10）

| 检查项 | 含义 |
|--------|------|
| C01 | 名称一致性（招标人 vs 正文） |
| C02 | 产品名称一致性 |
| C03 | 时间一致性（工期/节点） |
| C04 | 期限一致性（投标截止 vs 开标） |
| C05 | 金额一致性（大小写/单位） |
| C06 | 人员一致性（授权代表） |
| C07 | 章节完整性 |
| C08 | 星标项覆盖 |
| C09 | 废标条款自查 |
| C10 | 资质引用有效性 |

---

## 六、目录结构

```
QuickBid/
├── config.yaml              # 全局配置（路径 + AI provider）
├── models.py                # SQLAlchemy 数据模型
├── cli.py                   # 对话管理器（核心）
├── main.py                  # FastAPI REST API（非必须）
├── docs/
│   └── technical-design.md  # 本文档
├── materials/               # 材料库（6大类，永久积累）
│   ├── 01_公司资质/
│   ├── 02_业绩案例/
│   ├── 03_技术方案/
│   ├── 04_实施方案/
│   ├── 05_商务文件/
│   └── 06_其他/
├── projects/                # 项目目录（每个项目一个文件夹）
│   └── <timestamp>_<name>/
│       └── tender.pdf       # 招标文件固定路径
└── exports/                 # 导出文件
```

**固定路径约定：**
- 招标文件 → `projects/<timestamp>_<name>/tender.pdf`
- 导出文件 → `exports/tender_<project_id>.<fmt>`

---

## 七、技术选型

| 用途 | 选型 | 原因 |
|------|------|------|
| 对话管理 | 纯 Python（无 LangChain） | 状态机逻辑简单，引入 LangChain 反而增加复杂度 |
| 数据库 | SQLite + SQLAlchemy | 轻量、无需服务、本地持久化 |
| API 层 | FastAPI | 非必须，用于前端集成或 Web 化 |
| PDF 解析 | PyMuPDF | 速度快、文本提取准 |
| Word 导出 | python-docx | 成熟稳定 |
| PDF 导出 | WeasyPrint / LibreOffice | 候选 |
| AI | DeepSeek API（待接入） | 成本低、中文理解强 |

---

## 八、设计原则与教训

### 8.1 设计原则

1. **固定路径，不传递路径参数**  
   文件路径由系统生成并存储在 DB，用户始终通过「放好了」等语义触发，而非手动输入路径。

2. **每个状态只处理本状态的事**  
   Handler 之间无交叉依赖，状态转换是唯一出口。

3. **会话持久化做到最细粒度**  
   每一步操作后立即保存 `context`，支持中途退出、跨 session 恢复。

4. **AI 做一步，用户确认一步**  
   不在用户确认前做不可逆操作（如写文件、发请求）。

### 8.2 已踩过的坑

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| SQLAlchemy 2.0 `DeclarativeBase()` 直接实例化报错 | `Base = DeclarativeBase()` 而非 `class Base(DeclarativeBase)` | 显式继承 |
| WorkflowStep 用 `Enum` 导致 `step == WorkflowStep.IDLE` 恒为 False | 字符串子类要用 `str.__eq__`，不能用 Enum 比较 | 用纯字符串子类 `class WorkflowStep(str)` |
| CLI 测试用 stdin pipe 导致 EOFError | input() 在 pipe 模式下遇到 EOF | 写测试脚本直接调用 `handle()` 方法 |
| materials/ 目录无法 git add | `.gitignore` 中有 `materials/` 规则 | 覆盖 `.gitignore` 并用 `git add -f` |

---

## 九、待实现功能（TODO）

| 优先级 | 功能 | 说明 |
|--------|------|------|
| P0 | DeepSeek API 接入（解析） | K01-K14 提取 |
| P0 | DeepSeek API 接入（生成） | 初稿拼接 + 偏离表 |
| P1 | 材料库导入（批量） | 扫描 materials/ 目录自动索引 |
| P1 | 陪标模式 | 商务资质除外，AI 全量生成 |
| P2 | Word 导出（含目录/页眉页脚） | python-docx |
| P2 | PDF 导出 | WeasyPrint |
| P3 | Web 前端（可选） | 复用 main.py REST API |
| P3 | 多语言支持 | 英文投标文件 |

---

## 十、License

MIT
