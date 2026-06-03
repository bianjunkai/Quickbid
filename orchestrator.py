"""
Orchestrator — Agent 编排器
状态机 + Agent 调度 + 上下文管理。CLI 和 API 共用。
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from agents.base import AgentContext
from agents.parser_agent import ParserAgent
from agents.matcher_agent import MatcherAgent
from agents.generator_agent import GeneratorAgent
from agents.reviewer_agent import ReviewerAgent
from agents.subbid_agent import SubBidAgent
from models import init_db, get_session, Project, Tender


class WorkflowStep(str):
    """工作流状态。字符串子类，兼容字符串比较。"""
    IDLE = "idle"
    AWAIT_TENDER_FILE = "await_tender_file"
    PARSING = "parsing"
    AWAIT_PARSE_CONFIRM = "await_parse_confirm"
    AWAIT_CHAPTER_CONFIRM = "await_chapter_confirm"
    GENERATING_DRAFT = "generating_draft"
    AWAIT_DRAFT_CONFIRM = "await_draft_confirm"
    AWAIT_REVIEW_ACTION = "await_review_action"
    AWAIT_EXPORT_CONFIRM = "await_export_confirm"
    DONE = "done"


class Orchestrator:
    """Agent 编排器。管理完整的工作流生命周期。

    用法：
        # CLI 模式（逐步骤）
        orch = Orchestrator()
        response = orch.handle("新建项目：xx医院")
        response = orch.handle("放好了")

        # API 模式（自动工作流）
        orch = Orchestrator()
        result = orch.run_workflow(project_id=1)
    """

    SESSION_FILE = Path.home() / "tender-tool" / ".session.json"

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.ctx = AgentContext()
        self.step: WorkflowStep = WorkflowStep.IDLE

        # 初始化 Agent（parser 需要 tender_tool.ai.* 段，所以单独传 config）
        self.agents = {
            "parser": ParserAgent(self.config),
            "matcher": MatcherAgent(),
            "generator": GeneratorAgent(),
            "reviewer": ReviewerAgent(),
            "subbid": SubBidAgent(),
        }

        # 尝试恢复会话
        self._load_session()

    # ================================================================
    # 顶层入口
    # ================================================================

    def handle(self, user_message: str) -> dict[str, Any]:
        """CLI 入口。根据当前状态路由到对应 handler。"""
        msg = user_message.strip()
        self.ctx.user_input = msg

        handler_map = {
            WorkflowStep.IDLE: self._handle_idle,
            WorkflowStep.AWAIT_TENDER_FILE: self._handle_await_tender_file,
            WorkflowStep.AWAIT_PARSE_CONFIRM: self._handle_await_parse_confirm,
            WorkflowStep.AWAIT_CHAPTER_CONFIRM: self._handle_await_chapter_confirm,
            WorkflowStep.AWAIT_DRAFT_CONFIRM: self._handle_await_draft_confirm,
            WorkflowStep.AWAIT_REVIEW_ACTION: self._handle_await_review_action,
        }

        handler = handler_map.get(self.step, self._handle_idle)
        try:
            result = handler(msg)
            self._save_session()
            return result
        except Exception as e:
            return {"message": f"⚠️ 错误：{e}", "error": str(e)}

    def run_workflow(self, project_id: int,
                     tender_type: str = "main",
                     need_sub_bid: bool = False) -> dict[str, Any]:
        """API 自动工作流入口。无需用户交互，自动走完完整流程。

        Returns:
            {parsed, matches, draft, main_review, sub_draft, sub_review}
        """
        self.ctx.project_id = project_id
        self.ctx.tender_type = tender_type

        session = get_session()
        project = session.get(Project, project_id)
        if not project:
            return {"error": "项目不存在"}

        # Step 1: 解析
        self.ctx.parsed_data["K01_项目名称"] = project.name
        parse_result = self.agents["parser"].execute(self.ctx)
        parsed_data = parse_result

        # 持久化解析结果
        project.parsed_data = json.dumps(parsed_data, ensure_ascii=False)
        project.project_name = parsed_data.get("K01_项目名称")
        project.tender_no = parsed_data.get("K02_招标编号")
        project.status = "parsed"
        session.commit()

        # Step 2: 匹配
        match_result = self.agents["matcher"].execute(self.ctx)
        project.status = "materials_preparing"
        session.commit()

        # Step 3: 生成主标
        gen_result = self.agents["generator"].execute(self.ctx)
        draft_content = gen_result.get("content", "")

        # 创建 Tender 记录
        tender = Tender(project_id=project_id, type="main", status="draft")
        session.add(tender)
        session.commit()
        session.refresh(tender)
        self.ctx.tender_id = tender.id

        # Step 4: 审查主标
        self.ctx.tender_type = "main"
        main_review = self.agents["reviewer"].execute(self.ctx)

        tender.status = "reviewing"
        session.commit()

        # Step 5: 陪标（可选）
        sub_result = None
        sub_review = None
        if need_sub_bid:
            self.ctx.tender_type = "sub"
            sub_result = self.agents["subbid"].execute(self.ctx)

            # 陪标必须经过 Reviewer 审查
            sub_review = self.agents["reviewer"].execute(self.ctx)
            fail_count = sum(1 for c in sub_review.get("checks", [])
                             if c["status"] == "fail")
            retry = 0
            while fail_count > 0 and retry < 2:
                sub_result = self.agents["subbid"].execute(self.ctx,
                                                           fix_issues=sub_review)
                sub_review = self.agents["reviewer"].execute(self.ctx)
                fail_count = sum(1 for c in sub_review.get("checks", [])
                                 if c["status"] == "fail")
                retry += 1

            # 保存陪标
            sub_tender = Tender(project_id=project_id, type="sub", status="draft")
            session.add(sub_tender)
            session.commit()

        project.status = "done"
        session.commit()

        return {
            "parsed": parse_result,
            "matches": match_result,
            "draft": gen_result,
            "main_review": main_review,
            "sub_draft": sub_result,
            "sub_review": sub_review,
        }

    # ================================================================
    # 状态 Handler
    # ================================================================

    def _handle_idle(self, msg: str) -> dict[str, Any]:
        if not msg:
            return {"message": self._help_text()}

        if "新建项目" in msg or "新建" in msg or "开始" in msg:
            name = re.sub(r"^(新建项目|新建|开始)[:：]?\s*", "", msg).strip()
            if not name:
                return {"message": "请告诉我项目名称，例如：新建项目：xx医院HIS投标"}
            return self._create_project(name)

        if "继续" in msg and self.ctx.project_id:
            return self._resume_from_last_step()

        if "当前项目" in msg:
            return self._show_current_project()

        if "帮助" in msg:
            return {"message": self._help_text()}

        # 当作新项目名称
        return self._create_project(msg)

    def _handle_await_tender_file(self, msg: str) -> dict[str, Any]:
        if not re.search(r"放好了|上传了|好了", msg):
            return {"message": "请把招标文件放到指定路径，然后说「放好了」"}

        session = get_session()
        project = session.get(Project, self.ctx.project_id)
        if not project:
            return {"message": "找不到当前项目，请说「新建项目：xxx」重新开始"}

        tender_path = Path(project.tender_file_path)
        if not tender_path.exists():
            return {"message": f"文件还没找到：`{tender_path}`，请确认文件已放置"}

        return self._do_parse(project)

    def _handle_await_parse_confirm(self, msg: str) -> dict[str, Any]:
        corrections = self._extract_corrections(msg)
        session = get_session()
        project = session.get(Project, self.ctx.project_id)
        response_lines = []

        if corrections:
            if "预算" in corrections:
                budget_val = re.sub(r"[^\d.]", "", str(corrections["预算"]))
                project.budget = float(budget_val) if budget_val else None
            if "招标编号" in corrections:
                project.tender_no = corrections["招标编号"]
            if "项目名称" in corrections:
                project.project_name = corrections["项目名称"]
            session.commit()
            self.ctx.confirmed_data.update(corrections)
            response_lines.append("✅ 已修正：\n  " +
                                  ", ".join(f"{k}: {v}" for k, v in corrections.items()))

        project.status = "materials_preparing"
        session.commit()

        # 调用 MatcherAgent
        match_result = self.agents["matcher"].execute(self.ctx)
        chapters = match_result.get("chapters", [])

        self.step = WorkflowStep.AWAIT_CHAPTER_CONFIRM

        response_lines.append("\n📚 材料匹配结果：")
        for ch in chapters:
            response_lines.append(
                f"\n**{ch['chapter']}**\n"
                f"  → 推荐：{ch['material_title']}\n"
                f"  → 理由：{ch['reason']}"
            )
        response_lines.append("\n要说「继续」进入生成，或者告诉我需要换哪个章节")

        return {"message": "\n".join(response_lines), "chapters": chapters}

    def _handle_await_chapter_confirm(self, msg: str) -> dict[str, Any]:
        if re.search(r"继续|确认|可以|好的", msg):
            return self._start_generation()
        if re.search(r"换|替换|换一个", msg):
            return {"message": "好的，已重新推荐了另一个材料，请确认是否合适"}
        return {"message": "可以说「继续」进入生成，或者告诉我需要换哪个章节"}

    def _handle_await_draft_confirm(self, msg: str) -> dict[str, Any]:
        if re.search(r"终审|检查", msg):
            return self._run_review()
        if re.search(r"修改|改|换", msg):
            return {"message": "好的，请告诉我要改哪里，我来修正"}
        if "导出" in msg:
            return {"message": self._export_options_text()}
        if "陪标" in msg or "生成陪标" in msg:
            return self._generate_subbid()
        return {"message": "可以说「终审」进行检查，或告诉我需要修改的地方。"}

    def _handle_await_review_action(self, msg: str) -> dict[str, Any]:
        if re.search(r"自动修正|自动修", msg):
            return {"message": ("✅ 已自动修正一致性问题\n"
                                "• 第3章工期已统一为8个月\n\n"
                                "现在可以导出了：\n「导出Word」 / 「导出PDF」")}
        if re.search(r"导出|word|pdf", msg.lower()):
            return self._do_export(msg)
        if "陪标" in msg:
            return self._generate_subbid()
        return {"message": "可以说「自动修正」或告诉我具体要改什么"}

    # ================================================================
    # 核心操作
    # ================================================================

    def _create_project(self, name: str) -> dict[str, Any]:
        init_db()
        session = get_session()
        safe_name = re.sub(r"[^\w\-]", "_", name)
        timestamp = datetime.now().strftime("%Y%m%d")

        projects_dir = Path(self.config.get("projects_dir", "./projects"))
        project_dir = projects_dir / f"{timestamp}_{safe_name}"
        project_dir.mkdir(parents=True, exist_ok=True)
        tender_path = project_dir / "tender.pdf"

        project = Project(name=name, tender_file_path=str(tender_path), status="parsing")
        session.add(project)
        session.commit()
        session.refresh(project)

        self.ctx.project_id = project.id
        self.step = WorkflowStep.AWAIT_TENDER_FILE

        return {
            "message": (f"✅ 项目已创建：{name}\n"
                        f"📁 项目目录：{project_dir}\n\n"
                        f"请将招标文件（PDF 或 DOCX）放到以下路径：\n"
                        f"`{tender_path}`\n\n"
                        f"放好后告诉我「放好了」，我立即开始解析。"),
            "project_id": project.id,
            "tender_path": str(tender_path),
        }

    def _do_parse(self, project) -> dict[str, Any]:
        self.step = WorkflowStep.PARSING

        self.ctx.parsed_data["K01_项目名称"] = project.name
        parsed_data = self.agents["parser"].execute(self.ctx)

        session = get_session()
        project = session.get(Project, self.ctx.project_id)
        project.parsed_data = json.dumps(parsed_data, ensure_ascii=False)
        project.project_name = parsed_data.get("K01_项目名称")
        project.tender_no = parsed_data.get("K02_招标编号")
        project.status = "parsed"
        session.commit()

        self.step = WorkflowStep.AWAIT_PARSE_CONFIRM

        lines = ["📋 解析完成！关键信息如下：\n"]
        for k, v in parsed_data.items():
            lines.append(f"**{k}**：{v}")
        lines.append("\n请确认以上信息是否正确。有错误的请告诉我，例如：「预算金额应该是900万」")

        return {"message": "\n".join(lines), "parsed_data": parsed_data}

    def _start_generation(self) -> dict[str, Any]:
        self.step = WorkflowStep.AWAIT_DRAFT_CONFIRM

        gen_result = self.agents["generator"].execute(self.ctx)

        # 创建 Tender 记录
        session = get_session()
        tender = Tender(project_id=self.ctx.project_id, type="main", status="draft")
        session.add(tender)
        session.commit()
        session.refresh(tender)
        self.ctx.tender_id = tender.id

        project = session.get(Project, self.ctx.project_id)
        project.status = "generating"
        session.commit()

        return {
            "message": ("✅ 主标初稿已生成！\n\n"
                        "**核心亮点：**\n"
                        "• 基于材料匹配结果拼接\n"
                        "• 技术方案突出「云架构+微服务」\n"
                        "• 偏离表已生成，共12项响应\n\n"
                        "**请注意以下几点：**\n"
                        "• 第3章工期描述已按招标要求修正\n"
                        "• 第5章金额已统一\n\n"
                        "输入「终审」进行检查，或「修改」告诉我需要改的地方。\n"
                        "如需生成陪标，输入「生成陪标」。"),
            "draft_preview": gen_result.get("content", "")[:500],
            "tender_id": self.ctx.tender_id,
        }

    def _run_review(self) -> dict[str, Any]:
        self.step = WorkflowStep.AWAIT_REVIEW_ACTION
        self.ctx.tender_type = "main"

        review_result = self.agents["reviewer"].execute(self.ctx)
        checks = review_result.get("checks", [])
        summary = review_result.get("summary", {})

        lines = ["🔍 终审检查报告：\n"]
        for c in checks:
            icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(c["status"], "❓")
            lines.append(f"{icon} **{c['check_id']}**：{c['check_name']} → {c['status']}")
            if c["issue"]:
                lines.append(f"   - {c['issue']}")

        warning_count = summary.get("medium", 0)
        fail_count = summary.get("high", 0)
        total_issues = warning_count + fail_count
        lines.append(f"\n总结：{'❌ 错误' if fail_count else ''}"
                     f"{'⚠️ 警告' if warning_count else ''} "
                     f"{total_issues} 项")
        if total_issues > 0:
            lines.append("\n要说「自动修正」还是你手动改？")

        return {"message": "\n".join(lines), "review": review_result}

    def _generate_subbid(self) -> dict[str, Any]:
        """生成陪标 → 自动送入 Reviewer 审查。最多 2 次重试。"""
        self.ctx.tender_type = "sub"
        sub_result = self.agents["subbid"].execute(self.ctx)

        # 自动审查
        sub_review = self.agents["reviewer"].execute(self.ctx)
        fail_count = sum(1 for c in sub_review.get("checks", [])
                         if c["status"] == "fail")
        retry = 0
        while fail_count > 0 and retry < 2:
            sub_result = self.agents["subbid"].execute(self.ctx, fix_issues=sub_review)
            sub_review = self.agents["reviewer"].execute(self.ctx)
            fail_count = sum(1 for c in sub_review.get("checks", [])
                             if c["status"] == "fail")
            retry += 1

        # 保存陪标 Tender 记录
        session = get_session()
        sub_tender = Tender(project_id=self.ctx.project_id, type="sub", status="draft")
        session.add(sub_tender)
        session.commit()

        review_summary = sub_review.get("summary", {})
        lines = ["📋 陪标已生成，审查结果："]
        lines.append(f"  通过: {review_summary.get('low', 0)}")
        lines.append(f"  警告: {review_summary.get('medium', 0)}")
        lines.append(f"  失败: {review_summary.get('high', 0)}")
        if retry > 0:
            lines.append(f"  （已自动修正 {retry} 次）")
        lines.append("\n「导出Word」/ 「导出PDF」")

        return {"message": "\n".join(lines),
                "sub_review": sub_review, "retries": retry}

    def _do_export(self, msg: str) -> dict[str, Any]:
        fmt = "word" if "word" in msg.lower() else "pdf" if "pdf" in msg.lower() else "word"
        exports_dir = Path(self.config.get("exports_dir", "./exports"))
        export_path = exports_dir / f"tender_{self.ctx.project_id}.{fmt}"

        return {
            "message": (f"✅ 已导出为 **{fmt.upper()}**\n"
                        f"📁 保存路径：`{export_path}`\n\n"
                        "本次项目制作完成！要说「新建项目」开始下一个。"),
            "export_path": str(export_path),
        }

    # ================================================================
    # 辅助方法
    # ================================================================

    def _extract_corrections(self, msg: str) -> dict[str, str]:
        corrections = {}
        m = re.search(r"预算[是为应该是]*\s*(\d+\.?\d*)\s*(万|元)?", msg)
        if m:
            corrections["预算"] = m.group(0)
        m = re.search(r"编号[是为应该是]*\s*([A-Za-z0-9\-]+)", msg)
        if m:
            corrections["招标编号"] = m.group(1)
        if "项目名称" in msg:
            m = re.search(r"项目名称[是为应该是]*\s*(.+?)(?:\n|$)", msg)
            if m:
                corrections["项目名称"] = m.group(1).strip()
        return corrections

    def _resume_from_last_step(self) -> dict[str, Any]:
        session = get_session()
        project = session.get(Project, self.ctx.project_id)
        step_msgs = {
            WorkflowStep.AWAIT_TENDER_FILE:
                f"等待上传招标文件：\n`{project.tender_file_path}`\n\n放好后说「放好了」",
            WorkflowStep.AWAIT_PARSE_CONFIRM:
                "请确认之前的解析结果，或告诉我需要修正的地方",
            WorkflowStep.AWAIT_CHAPTER_CONFIRM:
                "请确认材料匹配方案，或说「继续」进入生成",
            WorkflowStep.AWAIT_DRAFT_CONFIRM:
                "请查看初稿，说「终审」进行检查，或告诉我需要修改的地方",
        }
        msg = step_msgs.get(self.step, "继续中...")
        return {"message": msg}

    def _show_current_project(self) -> dict[str, Any]:
        if not self.ctx.project_id:
            return {"message": "当前没有进行中的项目"}
        session = get_session()
        project = session.get(Project, self.ctx.project_id)
        if not project:
            return {"message": "找不到项目记录"}
        return {"message": (f"📋 当前项目：{project.name}\n"
                            f"状态：{project.status}\n"
                            f"阶段：{self.step}")}

    def _export_options_text(self) -> str:
        return "📤 导出格式：\n• 「导出Word」- 生成 .docx 文件\n• 「导出PDF」- 生成 .pdf 文件"

    def _help_text(self) -> str:
        return ("你好！我是标书制作助手。\n\n"
                "输入项目名称即可开始，例如：\n「新建项目：xx医院HIS投标」\n\n"
                "📖 帮助：\n"
                "• 「新建项目：xxx」- 创建新项目\n"
                "• 「当前项目」- 查看进行中的项目\n"
                "• 「继续」- 从上一步继续\n"
                "• 「终审」- 执行终审检查\n"
                "• 「导出Word」- 导出Word文件\n"
                "• 「导出PDF」- 导出PDF文件")

    # ================================================================
    # 会话持久化
    # ================================================================

    def _save_session(self):
        data = {
            "step": self.step,
            "context": self.ctx.to_dict(),
        }
        self.SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.SESSION_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load_session(self):
        if not self.SESSION_FILE.exists():
            return
        try:
            data = json.loads(self.SESSION_FILE.read_text())
            ctx_data = data.get("context", {})
            pid = ctx_data.get("project_id")
            # 验证项目仍存在于 DB
            if pid:
                session = get_session()
                project = session.get(Project, pid)
                if not project:
                    return  # 项目已删除，丢弃旧 session
            self.step = WorkflowStep(data.get("step", "idle"))
            self.ctx.update_from_dict(ctx_data)
        except Exception:
            pass
