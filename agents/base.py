"""
Agent 抽象基类 + AgentContext
所有 Agent 的无状态基础设施
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AgentContext:
    """Agent 执行上下文，由 Orchestrator 注入。
    每个 Agent 不持有状态，所有上下文外部化。"""

    project_id: Optional[int] = None
    tender_id: Optional[int] = None
    tender_type: str = "main"

    # 解析模式覆盖（None = 用 config.parser.mode 里的默认）
    parser_mode_override: Optional[str] = None

    # 解析产物
    parsed_data: dict[str, Any] = field(default_factory=dict)

    # 用户确认/修正后的数据
    confirmed_data: dict[str, Any] = field(default_factory=dict)

    # 材料列表
    materials: list[dict[str, Any]] = field(default_factory=list)

    # 章节-材料映射
    chapters: list[dict[str, Any]] = field(default_factory=list)

    # 标书初稿内容
    draft_content: str = ""
    sub_draft_content: str = ""

    # 审查报告
    review_report: dict[str, Any] = field(default_factory=dict)

    # 用户最近输入
    user_input: str = ""

    # 错误信息（Agent 执行失败时填充）
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "tender_id": self.tender_id,
            "tender_type": self.tender_type,
            "parsed_data": self.parsed_data,
            "confirmed_data": self.confirmed_data,
            "chapters": self.chapters,
            "review_report": self.review_report,
        }

    def update_from_dict(self, data: dict) -> None:
        for key in ("project_id", "tender_id", "tender_type",
                     "parsed_data", "confirmed_data", "chapters", "review_report"):
            if key in data:
                setattr(self, key, data[key])


class BaseAgent(ABC):
    """Agent 抽象基类。所有 Agent 必须实现 execute() 和 validate_output()。"""

    name: str = "base"
    description: str = "Base agent"
    system_prompt: str = ""
    model: str = "deepseek-chat"
    temperature: float = 0.1

    @abstractmethod
    def execute(self, ctx: AgentContext) -> dict[str, Any]:
        """执行 Agent 任务，返回结构化结果。

        Args:
            ctx: 当前 AgentContext，包含所有上游数据

        Returns:
            结构化 dict，具体 schema 由各 Agent 定义
        """
        ...

    def validate_output(self, output: dict[str, Any]) -> bool:
        """验证输出结构是否完整。默认不做校验，子类覆盖。"""
        return True

    def _build_messages(self, user_content: str) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} model={self.model} temp={self.temperature}>"
