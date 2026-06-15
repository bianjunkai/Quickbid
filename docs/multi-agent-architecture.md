# QuickBid 多 Agent 架构设计

> 本文档记录 QuickBid v3 从"单 AI 调用"重构为"多 Agent 协作"的核心架构设计。
> 前置阅读：[technical-design.md](./technical-design.md)

## 一、为什么需要多 Agent 架构

### 当前（v2）模式的问题

```
用户输入 → 状态机路由 → 调用全能力 DeepSeek API → 返回结果 → 用户确认
```

痛点：
- 每个步骤的 prompt 越来越长（需要包含所有上下文 + 所有规则）
- 单一 Agent 在解析、匹配、生成、审查四个截然不同的任务间切换，输出质量不稳定
- 无法为不同任务选择不同模型/参数（解析需要低温度精确提取、生成需要创造性）
- 难以独立测试和迭代单个环节

### v3 多 Agent 模式

```
用户输入 → Orchestrator（状态机 + Agent 调度）
                ├── ParserAgent      → 结构化提取 K01-K14
                ├── MatcherAgent     → 材料-章节智能匹配
                ├── GeneratorAgent   → 标书初稿生成
                ├── ReviewerAgent    → C01-C10 终审检查
                └── SubBidAgent      → 陪标独立生成
```

每个 Agent 是**特化的小型 AI**，有专属 system prompt、专属工具集、独立的输出 schema。

---

## 二、Agent 定义

### Agent 基类

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class AgentContext:
    """Agent 执行上下文，由 Orchestrator 注入"""
    project_id: int
    parsed_data: dict = None
    confirmed_data: dict = None
    materials: list = None
    chapters: list = None
    draft_content: str = None

class BaseAgent(ABC):
    """Agent 抽象基类"""
    
    name: str                          # Agent 标识
    description: str                   # 职责描述
    system_prompt: str                 # 专属系统提示词
    model: str = "deepseek-chat"       # 可独立选择模型
    temperature: float = 0.1           # 可独立设定温度
    
    @abstractmethod
    def execute(self, ctx: AgentContext, user_input: Optional[str] = None) -> dict:
        """执行 Agent 任务，返回结构化结果"""
        pass
    
    @abstractmethod
    def validate_output(self, output: dict) -> bool:
        """验证输出结构是否完整"""
        pass
```

### ParserAgent — 招标文件解析

| 属性 | 值 |
|------|-----|
| 职责 | 从招标文件中提取 K01-K14 结构化信息 |
| system_prompt | "你是招标文件分析专家。从原始文本中精确提取关键信息..." |
| temperature | 0.0（最确定，不允许创造） |
| 输入 | PDF/DOCX 文本 + K01-K14 schema |
| 输出 | `{K01: str, K02: str, ..., K14: str}` JSON |
| 工具 | `file_utils.extract_text()` — 读取 PDF/DOCX |
| 特点 | 只做提取，不做推理。找不到的字段填 "未找到"，由用户人工补充 |

### MatcherAgent — 提纲设计 + 材料匹配

| 属性 | 值 |
|------|-----|
| 职责 | 基于 K01-K14 设计章节大纲，并将章节与材料库进行智能匹配 |
| system_prompt | "你是医院信息化投标文件的标书结构规划师..." |
| temperature | 0.1 |
| 输入 | K01-K14 全字段 + scoring_breakdown（评分详细子项）+ 材料库列表 |
| 输出 | `{outline: [{id, no, title, category, subsections}], chapters: [{chapter_id, material_id, match_score}], validation: {...}}` |
| 工具 | LLM 生成提纲 + 分类精确匹配 + 关键词子串匹配 |
| 特点 | **两阶段工作流**：(1) `generate_outline()` — LLM 设计 2 级章节大纲；(2) `match_materials()` — 用确认后的提纲做直接分类匹配。**静态验证**：`validate_outline()` 检查 5 个规则（评分项覆盖度、章节数量合理性、分类多样性、K12 模板遵从、重复检查），返回 warnings/errors。**自然语言修改**：`interpret_outline_command()` 解析用户的修改指令（删除/新增/重命名/修改小节），返回 action 指令由 Orchestrator 执行 |

**提纲验证规则**（Phase 0 新增）：
1. **评分项覆盖度** — `scoring.dimensions` 中带独立分值的 sub_items 是否在提纲的章节/小节标题中出现
2. **章节数量合理性** — 一级章节 3-10 个，每章小节 ≤10 个
3. **分类多样性** — 6 个标准分类至少用了 4 个（避免过度使用 06_其他）
4. **K12 模板遵从** — 如果 K12 是结构化目录，检查关键章节是否保留
5. **重复检查** — 章节标题不重复，小节标题不与父章节重复

验证结果包含 `is_valid`（是否有阻塞性错误）、`warnings`（警告列表）、`errors`（错误列表）和 `stats`（统计信息，含评分覆盖率）。前端展示：错误用红色卡片 + 禁用"继续"按钮，警告用黄色卡片但不阻塞流程。

### GeneratorAgent — 标书生成

| 属性 | 值 |
|------|-----|
| 职责 | 根据确认的材料和章节结构生成标书初稿 |
| system_prompt | "你是医疗信息化标书撰写专家。根据材料内容撰写专业标书章节..." |
| temperature | 0.3（适度创造性，生成流畅正文） |
| 输入 | 确认后的章节-材料映射 + 材料全文 + 项目上下文 |
| 输出 | Markdown 格式的标书初稿（含各级标题、表格、段落） |
| 特点 | 处理事实一致性（日期/金额/名称不瞎编），偏离表自动生成 |

### ReviewerAgent — 终审检查（主标 + 陪标）

| 属性 | 值 |
|------|-----|
| 职责 | 对主标和陪标初稿执行 C01-C10 10 项检查 |
| system_prompt | "你是标书质量审核专家。严格对照招标要求检查标书..." |
| temperature | 0.0 |
| 输入 | 标书初稿 + 标书类型标记（main/sub）+ 原始 parsed_data |
| 输出 | `[{check_id, check_name, status: pass/warning/fail, issue, suggestion}]` |
| 特点 | 只检查不修改。对 fail/warning 项给出具体修改建议。**主标和陪标都须经审查通过**。陪标特别关注：事实一致性（日期/金额/名称不能偏离招标要求）、商务资质完整性（必须与主标一致）、章节独立性（不能与主标雷同度太高） |

### SubBidAgent — 陪标生成

| 属性 | 值 |
|------|-----|
| 职责 | 独立生成陪标文件（与主标内容不同但事实一致） |
| system_prompt | "你是投标文件撰写专家。生成一份独立风格的陪标文件..." |
| temperature | 0.5（较高，确保内容多样化） |
| 输入 | 主标初稿 + 商务资质（不可变）+ 项目上下文 |
| 输出 | Markdown 格式的陪标初稿（流入 ReviewerAgent 进行审查） |
| 下游 | **产出必须经过 ReviewerAgent 审查**，不合格的陪标应重新生成 |
| 特点 | 商务资质逐字复制，其余章节独立生成，结构和措辞刻意差异化 |

---

## 三、Orchestrator 编排器

```python
class Orchestrator:
    """Agent 编排器 — 状态机 + Agent 调度"""
    
    def __init__(self):
        self.agents = {
            "parser": ParserAgent(),
            "matcher": MatcherAgent(),
            "generator": GeneratorAgent(),
            "reviewer": ReviewerAgent(),
            "subbid": SubBidAgent(),
        }
        self.state_machine = WorkflowStateMachine()
        self.ctx = AgentContext()
    
    def dispatch(self, state: str, user_input: str = None) -> dict:
        """根据当前状态调度对应 Agent"""
        
        agent_map = {
            "AWAIT_TENDER_FILE":  ("parser",     "开始解析招标文件"),
            "AWAIT_PARSE_CONFIRM": ("matcher",    "开始匹配材料"),
            "AWAIT_CHAPTER_CONFIRM": ("generator", "开始生成标书"),
            "AWAIT_DRAFT_CONFIRM": ("reviewer",   "开始终审检查"),
            "AWAIT_REVIEW_ACTION": (None,         "等待用户指令"),
        }
        
        agent_name, instruction = agent_map.get(state, (None, None))
        if agent_name:
            agent = self.agents[agent_name]
            return agent.execute(self.ctx, user_input)
        return {"message": "等待您的指令"}
    
    def inject_context(self, **kwargs):
        """用户确认后更新上下文，传递给下一个 Agent"""
        self.ctx.confirmed_data = {**self.ctx.confirmed_data, **kwargs}
    
    def run_workflow(self, project_id: int) -> dict:
        """端到端自动工作流（无用户交互模式，用于 API）"""
        self.ctx.project_id = project_id
        
        # 解析
        parse_result = self.agents["parser"].execute(self.ctx)
        self.ctx.parsed_data = parse_result
        
        # 匹配
        match_result = self.agents["matcher"].execute(self.ctx)
        self.ctx.confirmed_data = match_result
        
        # 生成
        gen_result = self.agents["generator"].execute(self.ctx)
        self.ctx.draft_content = gen_result.get("content")
        
        # 审查主标
        main_review = self.agents["reviewer"].execute(self.ctx, tender_type="main")
        
        # 陪标（可选）
        sub_result = None
        sub_review = None
        if self.ctx.need_sub_bid:
            sub_result = self.agents["subbid"].execute(self.ctx)
            self.ctx.sub_draft_content = sub_result.get("content")
            
            # 陪标也必须经过 Reviewer 审查
            sub_review = self.agents["reviewer"].execute(self.ctx, tender_type="sub")
            # 如有严重问题，退回重新生成
            fail_count = sum(1 for c in sub_review.get("checks", []) if c["status"] == "fail")
            retry = 0
            while fail_count > 0 and retry < 2:
                sub_result = self.agents["subbid"].execute(self.ctx, fix_issues=sub_review)
                self.ctx.sub_draft_content = sub_result.get("content")
                sub_review = self.agents["reviewer"].execute(self.ctx, tender_type="sub")
                fail_count = sum(1 for c in sub_review.get("checks", []) if c["status"] == "fail")
                retry += 1
        
        return {
            "parsed": parse_result,
            "matches": match_result,
            "draft": gen_result,
            "main_review": main_review,
            "sub_draft": sub_result,
            "sub_review": sub_review,
        }
```

---

## 四、工作流对比

### v2 模式（当前）

```
状态机 → ai_engine.parse() → mock 数据
状态机 → ai_engine.match() → mock 数据
状态机 → ai_engine.generate() → mock 消息
状态机 → ai_engine.review() → mock 报告
```

每个函数是**无结构化的 prompt 调用**，输出质量完全依赖单次 API 调用。

### v3 多 Agent 模式

```
Orchestrator.dispatch("AWAIT_TENDER_FILE")
  → ParserAgent.execute(ctx)
    → file_utils.extract_text(PDF) → 纯文本
    → DeepSeek(system_prompt, text, schema=K01_K14_SCHEMA)
    → 验证输出结构完整性
    → 返回结构化 K01-K14

Orchestrator.dispatch("AWAIT_PARSE_CONFIRM")
  → MatcherAgent.execute(ctx)
    → 从 DB 加载材料库（惰性缓存）
    → 关键词过滤 → 语义相似度排序
    → 返回 [{chapter, material, score, reason}]

Orchestrator.dispatch("AWAIT_CHAPTER_CONFIRM")
  → GeneratorAgent.execute(ctx)
    → 加载确认后的材料全文
    → DeepSeek(system_prompt, materials + context, temperature=0.3)
    → 事实一致性后处理（日期/金额 Cross-check）
    → 返回 Markdown 标书

Orchestrator.dispatch("AWAIT_DRAFT_CONFIRM")
  → ReviewerAgent.execute(ctx, tender_type="main")
    → DeepSeek(system_prompt, draft + parsed_data, temperature=0.0)
    → 逐项输出 C01-C10 检查结果
    → 返回 [{check_id, status, issue, suggestion}]

Orchestrator.dispatch("AWAIT_SUBBID")   # 用户选择生成陪标
  → SubBidAgent.execute(ctx)
    → 加载商务资质 + 主标结构
    → DeepSeek(system_prompt, main_draft + qualifications, temperature=0.5)
    → 返回 Markdown 陪标初稿
  → 自动进入审查
  → ReviewerAgent.execute(ctx, tender_type="sub")
    → 对陪标执行 C01-C10（特别检查：事实一致性、资质完整性、内容独立性）
    → 如 fail 项 ≥ 阈值，退回 SubBidAgent 重新生成
    → 返回 [{check_id, status, issue, suggestion}]
```

---

## 五、关键设计决策

### 5.1 Agent 无状态、上下文外部化

每个 Agent 不持有状态。所有状态由 Orchestrator 的 `AgentContext` 管理。Agent 只做：接收上下文 → 执行任务 → 返回结构化结果。

**原因：**
- Agent 可独立测试（传入 mock context）
- Agent 可替换（换更强大的模型，不改代码）
- 支持断点恢复（序列化 AgentContext 即可）

### 5.2 Agent 可独立升级

每个 Agent 可独立选择：
- 不同模型（DeepSeek / GPT / Claude）
- 不同温度参数
- 不同工具集
- 不同输出 schema

例如：ParserAgent 用 DeepSeek（便宜），GeneratorAgent 用 Claude（质量高），ReviewerAgent 用 DeepSeek（成本低但足以做检查）。

### 5.3 确认驱动不变

多 Agent 架构不改变"确认驱动对话"的核心范式：
- Orchestrator 调用 Agent → Agent 返回结果 → 用户确认/纠正 → Orchestrator 注入修正后的上下文 → 调度下一个 Agent
- 三句黄金法则（继续/修改/自动修正）依然适用

### 5.4 Agent 间通过结构化数据通信

Agent 之间不直接通信。所有数据通过 Orchestrator 的 `AgentContext` 传递，且必须使用结构化格式（JSON Schema 约束）。

---

## 六、文件结构

```
Quickbid/
├── agents/
│   ├── __init__.py              # 将 agents/ 暴露为 Python 包
│   ├── base.py                  # BaseAgent 抽象类 + AgentContext
│   ├── parser_agent.py          # ParserAgent
│   ├── matcher_agent.py         # MatcherAgent
│   ├── generator_agent.py       # GeneratorAgent
│   ├── reviewer_agent.py        # ReviewerAgent
│   └── subbid_agent.py          # SubBidAgent
├── orchestrator.py              # Orchestrator 编排器
├── cli.py                       # CLI 入口（调用 Orchestrator）
├── main.py                      # FastAPI 入口（调用 Orchestrator）
├── models.py                    # SQLAlchemy 数据模型（不变）
├── config.yaml                  # Agent 配置 + 模型选择
├── file_utils.py                # 文件解析工具（不变）
├── export_engine.py             # 导出引擎（不变）
└── ...
```

---

## 七、与现有代码的关系

| 现有文件 | 变化 |
|----------|------|
| `cli.py` | 状态机逻辑迁移到 `orchestrator.py`，cli.py 变为纯交互层 |
| `main.py` | FastAPI 端点调用 Orchestrator 而非直接写 mock |
| `models.py` | 不变，Agent 通过 Orchestrator 读写 DB |
| `ai_engine.py` | **不再需要**，各 Agent 自行封装 DeepSeek 调用 |

---

## 八、迁移策略

1. **Phase 0**：清理冗余代码（PyQt5 GUI、Design.md 重复文件）
2. **Phase 1**：修复阻塞性 bug，确保应用可运行
3. **Phase 2**：实现 `agents/base.py` + `orchestrator.py` 框架（先用 mock Agent）
4. **Phase 3**：逐个实现 Agent（Parser → Matcher → Generator → Reviewer → SubBid），每个 Agent 先 mock 后接入 DeepSeek
5. **Phase 4+**：材料库、导出、Web 前端（与 Agent 架构无关的外围功能）

---

*创建日期：2026-05-30 | 对应 Design.md Section 1-7*
