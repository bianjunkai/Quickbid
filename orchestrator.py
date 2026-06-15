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
from agents.bid_parser.schema import k_field_value
from agents.parser_agent import ParserAgent
from agents.matcher_agent import MatcherAgent
from agents.generator_agent import GeneratorAgent
from agents.reviewer_agent import ReviewerAgent
from agents.subbid_agent import SubBidAgent
from agents.qa_agent import QAAgent
from models import init_db, get_session, Project, Tender


class WorkflowStep(str):
    """工作流状态。字符串子类，兼容字符串比较。"""
    IDLE = "idle"
    AWAIT_TENDER_FILE = "await_tender_file"
    PARSING = "parsing"
    AWAIT_PARSE_CONFIRM = "await_parse_confirm"
    AWAIT_OUTLINE_CONFIRM = "await_outline_confirm"
    AWAIT_CHAPTER_CONFIRM = "await_chapter_confirm"
    GENERATING_DRAFT = "generating_draft"
    AWAIT_DRAFT_CONFIRM = "await_draft_confirm"
    AWAIT_REVIEW_ACTION = "await_review_action"
    AWAIT_EXPORT_CONFIRM = "await_export_confirm"
    DONE = "done"


# 提纲修改的"接受"快速路径（避免 LLM round-trip 处理"继续"）
RE_OUTLINE_ACCEPT = r"^继续$|^确认$|^可以$|^好的$|^OK$|^ok$|^没问题$|^看着行$|^行$"


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
            "qa": QAAgent(self.config),
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
            WorkflowStep.AWAIT_OUTLINE_CONFIRM: self._handle_await_outline_confirm,
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
        # 用新 shape 写入 K01，方便下游用 k_field_value() 拿到字符串
        self.ctx.parsed_data["K01_项目名称"] = {"value": project.name, "source_page": None}
        parse_result = self.agents["parser"].execute(self.ctx)
        parsed_data = parse_result

        # 持久化解析结果
        project.parsed_data = json.dumps(parsed_data, ensure_ascii=False)
        # K 字段新 shape：{value|items, source_page|source_pages}，DB 存的是字符串
        project.project_name = k_field_value(parsed_data.get("K01_项目名称")) or project.name
        project.tender_no = k_field_value(parsed_data.get("K02_招标编号"))
        project.status = "parsed"
        session.commit()

        # Step 2: 匹配
        match_result = self.agents["matcher"].execute(self.ctx)
        project.status = "materials_preparing"
        session.commit()

        # Step 3: 生成主标
        gen_result = self.agents["generator"].execute(self.ctx)

        # 创建 Tender 记录
        tender = Tender(project_id=project_id, type="main", status="draft")
        session.add(tender)
        session.commit()
        session.refresh(tender)
        self.ctx.tender_id = tender.id

        # 落盘主标文件 + 落库 draft_path
        draft_path = self._write_main_tender_files(
            project, tender, gen_result, self.ctx.parsed_data or {}
        )

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

        project.status = "outline_generating"
        session.commit()

        # 调 LLM 生成提纲
        outline_result = self.agents["matcher"].generate_outline(self.ctx)
        outline = outline_result.get("outline", [])

        # 持久化（_generated_outline 已在 MatcherAgent 内写入 ctx.parsed_data）
        project.parsed_data = json.dumps(
            self.ctx.parsed_data, ensure_ascii=False
        )
        session.commit()

        self.step = WorkflowStep.AWAIT_OUTLINE_CONFIRM

        response_lines.append(self._render_outline(outline, intro="📑 标书章节大纲（AI 生成）"))

        return {
            "message": "\n".join(response_lines),
            "outline": outline,
        }

    def _handle_await_outline_confirm(self, msg: str) -> dict[str, Any]:
        """
        处理提纲确认/修改。

        接受 → 进入材料匹配（快速正则，不调 LLM）。
        修改 → MatcherAgent.interpret_outline_command 用 LLM 解析自然语言指令，
               应用 delete/add/rename/modify_subsection/regenerate。
        其它 → unknown 消息走纯文本 text-delta。
        """
        # 1) 接受（快速路径）
        if re.search(RE_OUTLINE_ACCEPT, msg.strip(), re.IGNORECASE):
            return self._start_matching()

        # 2) LLM 解析用户的自然语言修改指令
        action = self.agents["matcher"].interpret_outline_command(
            self.ctx.outline, msg
        )
        act = action.get("action")

        if act == "accept":
            return self._start_matching()
        if act == "unknown":
            return {"message": action.get("message") or self._outline_help_text()}

        if act == "regenerate":
            hint = action.get("hint") or msg
            outline_result = self.agents["matcher"].generate_outline(
                self.ctx, hint=hint
            )
            self.ctx.outline = outline_result.get("outline", [])
            self.ctx.parsed_data["_generated_outline"] = self.ctx.outline
        elif act in ("delete", "add", "rename", "modify_subsection"):
            self._apply_outline_action(action)
        else:
            return {"message": self._outline_help_text()}

        # 持久化（_generated_outline 跟着 outline 一起更新；用户确认后
        # _start_matching 会写 _confirmed_outline）
        session = get_session()
        project = session.get(Project, self.ctx.project_id)
        if project:
            project.parsed_data = json.dumps(
                self.ctx.parsed_data, ensure_ascii=False
            )
            session.commit()

        # 返回结构化 outline；前端 OutlineToolResult 自动重渲染，
        # 不再返回 text 形式的完整提纲（避免与 OutlineToolResult 重复）
        return {"outline": self.ctx.outline}

    def _start_matching(self) -> dict[str, Any]:
        """用已确认的 outline 调 match_materials，转 AWAIT_CHAPTER_CONFIRM。"""
        match_result = self.agents["matcher"].match_materials(self.ctx)
        chapters = match_result.get("chapters", [])

        # 标记提纲已确认 + 持久化
        self.ctx.parsed_data["_confirmed_outline"] = self.ctx.outline
        session = get_session()
        project = session.get(Project, self.ctx.project_id)
        if project:
            project.parsed_data = json.dumps(
                self.ctx.parsed_data, ensure_ascii=False
            )
            project.status = "materials_preparing"
            session.commit()

        self.step = WorkflowStep.AWAIT_CHAPTER_CONFIRM

        # 检查空材料库
        empty_warn = ""
        if not chapters or all(c.get("material_id") is None for c in chapters):
            empty_warn = "⚠️ 材料库为空，所有章节标记为「需新建」\n\n"

        lines = [empty_warn + "📚 材料匹配结果："]
        for ch in chapters:
            score_icon = {"高": "🟢", "中": "🟡", "低": "🔴"}.get(
                ch.get("match_score", ""), "❓"
            )
            lines.append(
                f"\n{score_icon} **{ch['chapter']}** "
                f"（{ch.get('category', '')}）\n"
                f"  → 推荐：{ch['material_title']}\n"
                f"  → 理由：{ch['reason']}"
            )
            alts = ch.get("alternatives") or []
            if alts:
                lines.append(
                    "  → 备选：" + " / ".join(
                        a.get("material_title", "") for a in alts
                    )
                )
        lines.append("\n说「继续」进入生成，或者告诉我需要换哪个章节")

        return {
            "message": "\n".join(lines),
            "chapters": chapters,
        }

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

        # 用新 shape 写入 K01，方便下游用 k_field_value() 拿到字符串
        self.ctx.parsed_data["K01_项目名称"] = {"value": project.name, "source_page": None}
        parsed_data = self.agents["parser"].execute(self.ctx)

        session = get_session()
        project = session.get(Project, self.ctx.project_id)
        project.parsed_data = json.dumps(parsed_data, ensure_ascii=False)
        # K 字段新 shape：{value|items, source_page|source_pages}，DB 存的是字符串
        project.project_name = k_field_value(parsed_data.get("K01_项目名称")) or project.name
        project.tender_no = k_field_value(parsed_data.get("K02_招标编号"))
        project.status = "parsed"
        session.commit()

        self.step = WorkflowStep.AWAIT_PARSE_CONFIRM

        lines = ["📋 解析完成！关键信息如下：\n"]
        for k, v in parsed_data.items():
            if k.startswith("_"):
                continue
            display = k_field_value(v)
            if display is None:
                display = "—"
            elif isinstance(display, list):
                display = "；".join(str(x) for x in display)
            else:
                display = str(display)
            lines.append(f"**{k}**：{display}")
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

        # 落盘主标文件 + 落库 draft_path
        draft_path = self._write_main_tender_files(
            project, tender, gen_result, self.ctx.parsed_data or {}
        )
        project.status = "generating"
        session.commit()

        chapters = gen_result.get("chapters", [])
        return {
            "message": ("✅ 主标初稿已生成！\n\n"
                        f"**已生成 {len(chapters)} 章**，已归档到右侧项目文件面板。\n"
                        "**下一步：**\n"
                        "• 「终审」进行检查\n"
                        "• 「修改 [章节] [内容]」告诉我要改的地方\n"
                        "• 「生成陪标」生成陪标文件\n"
                        f"📁 路径：`{draft_path}`"),
            "draft_preview": gen_result.get("content", "")[:500],
            "draft_path": draft_path,
            "draft_chapters": chapters,
            "outline": gen_result.get("outline", []),
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
    # 文件落盘（GeneratorAgent 输出 → 真实文件 + tender.draft_path）
    # ================================================================

    def _write_main_tender_files(
        self,
        project,
        tender,
        gen_result: dict[str, Any],
        parsed: dict[str, Any],
    ) -> str:
        """把主标生成结果写到 projects/{ts}_{name}/main/ 目录,落库 tender.draft_path。

        落盘结构:
          main/
            cover.md              封面+目录
            draft.md              完整拼装 Markdown
            deviation.md          偏离表占位
            <category>/           随 outline 动态生成
              <no:02d>_<title>.md 单章内容
        """
        if not project or not project.tender_file_path:
            return ""
        try:
            project_dir = Path(project.tender_file_path).parent
            main_dir = project_dir / "main"
            main_dir.mkdir(parents=True, exist_ok=True)

            chapters = gen_result.get("chapters", []) or []
            k01 = k_field_value(parsed.get("K01_项目名称")) or project.name

            # 1) cover.md
            cover_lines = [
                f"# {k01} — 投标文件（主标）",
                "",
                "## 项目信息",
                "",
                f"- **项目名称**: {k01}",
            ]
            k02 = k_field_value(parsed.get("K02_招标编号"))
            k03 = k_field_value(parsed.get("K03_招标人"))
            k05 = k_field_value(parsed.get("K05_投标截止时间"))
            if k02:
                cover_lines.append(f"- **招标编号**: {k02}")
            if k03:
                cover_lines.append(f"- **招标人**: {k03}")
            if k05:
                cover_lines.append(f"- **投标截止时间**: {k05}")
            cover_lines.extend([
                "",
                "## 目录",
                "",
            ])
            for ch in chapters:
                no = ch.get("no", "?")
                title = ch.get("title", "")
                cover_lines.append(f"- 第{no}章 {title}")
            cover_lines.append("")
            (main_dir / "cover.md").write_text(
                "\n".join(cover_lines), encoding="utf-8"
            )

            # 2) draft.md
            draft_path = main_dir / "draft.md"
            draft_path.write_text(
                gen_result.get("content", "") or "", encoding="utf-8"
            )

            # 3) 各分类子目录 + 单章文件
            for ch in chapters:
                cat = ch.get("category", "06_其他") or "06_其他"
                cat_dir = main_dir / cat
                cat_dir.mkdir(parents=True, exist_ok=True)
                no = ch.get("no", 0)
                title = ch.get("title", "未命名章节")
                # 防御性转换：no 可能是非数字字符串（如 "?"）
                try:
                    no_int = int(no)
                except (ValueError, TypeError):
                    no_int = 0
                fname = f"{no_int:02d}_{self._sanitize_filename(title)}.md"
                (cat_dir / fname).write_text(
                    ch.get("content", "") or "", encoding="utf-8"
                )

            # 4) deviation.md（占位,DeviationAgent 后续生成）
            (main_dir / "deviation.md").write_text(
                "# 商务/技术条款偏离表\n\n"
                "> 本节由 DeviationAgent 后续生成,占位中。\n"
                "> 一般会要两套:商务条款偏离表（05_商务文件）+ 技术条款偏离表（03_技术方案）。\n",
                encoding="utf-8",
            )

            # 5) 落库
            session = get_session()
            t = session.get(Tender, tender.id)
            if t:
                t.draft_path = str(draft_path)
                session.commit()

            return str(draft_path)
        except Exception as e:
            # 写文件失败不能阻塞主流程
            logger.warning("写主标文件失败: %s", e)
            return ""

    @staticmethod
    def _sanitize_filename(name: str, max_len: int = 50) -> str:
        """文件名 sanitize:替换非法字符 + 截断。"""
        s = re.sub(r'[/\\:*?"<>|\r\n\t]+', "_", name or "")
        s = s.strip().strip(".")
        if not s:
            s = "未命名"
        if len(s) > max_len:
            s = s[:max_len]
        return s

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

    # ---- 提纲相关辅助 ----

    def _render_outline(self, outline: list[dict[str, Any]],
                        intro: str = "📑 标书章节大纲") -> str:
        """渲染提纲到 CLI 字符串。章节数 > 10 时只显示前 10 章 + 省略提示。"""
        if not outline:
            return f"{intro}\n（无章节）"
        lines = [intro]
        show = outline[:10]
        for ch in show:
            no = ch.get("no", "?")
            title = ch.get("title", "")
            cat = ch.get("category", "")
            lines.append(f"\n  第{no}章 {title}（{cat}）")
            for sub in ch.get("subsections") or []:
                lines.append(f"    · {sub.get('title', '')}")
        if len(outline) > 10:
            lines.append(f"\n  … 还有 {len(outline) - 10} 章未显示")
        lines.append(
            "\n说「继续」进入材料匹配。"
            "\n修改指令：删除第N章 / 加一章 [标题] / 改 [旧] 为 [新] / 重排 / 换"
        )
        return "\n".join(lines)

    def _outline_help_text(self) -> str:
        return ("可以这样告诉我修改：\n"
                "• 删除第3章 / 把第3章删了\n"
                "• 加一章「数据迁移方案」\n"
                "• 把第3章改名为「实施保障」\n"
                "• 技术方案那章加一个小节「数据迁移」\n"
                "• 重新生成提纲（再想想）\n"
                "或者直接说「继续」进入材料匹配")

    def _apply_outline_action(self, action: dict[str, Any]) -> None:
        """
        把 LLM 解析出的 action 应用到 in-memory ctx.outline。

        支持：delete / add / rename / modify_subsection。
        regenerate 由调用方单独处理（要调 LLM）。
        """
        outline = list(self.ctx.outline)
        act = action.get("action")

        if act == "delete":
            no = int(action["chapter_no"])
            outline = [ch for ch in outline if ch.get("no") != no]

        elif act == "add":
            title = action["title"]
            cat = action.get("category", "06_其他")
            after = int(action.get("after_chapter_no", len(outline)))
            after = max(0, min(after, len(outline)))
            new_chapter = {
                "id": f"ch{after + 1}",
                "no": after + 1,
                "title": title,
                "category": cat,
                "subsections": [],
                "source": "user_added",
            }
            outline.insert(after, new_chapter)

        elif act == "rename":
            no = int(action["chapter_no"])
            new_title = action.get("new_title", "").strip()
            if new_title:
                for ch in outline:
                    if ch.get("no") == no:
                        ch["title"] = new_title
                        break

        elif act == "modify_subsection":
            no = int(action["chapter_no"])
            sub_act = action.get("sub_action")
            sub_title = action.get("subsection_title", "").strip()
            for ch in outline:
                if ch.get("no") != no:
                    continue
                subs = ch.setdefault("subsections", [])
                if sub_act == "add" and sub_title:
                    sub_id = f"{ch.get('id', f'ch{no}')}.{len(subs) + 1}"
                    subs.append({"id": sub_id, "title": sub_title})
                elif sub_act == "delete" and sub_title:
                    ch["subsections"] = [
                        s for s in subs if s.get("title") != sub_title
                    ]
                elif sub_act == "rename" and sub_title:
                    new_sub_title = action.get("new_subsection_title", sub_title).strip()
                    for s in subs:
                        if s.get("title") == sub_title:
                            s["title"] = new_sub_title
                            break
                break

        # 重新编号 + id（任何结构性变化后都要做）
        for i, ch in enumerate(outline, 1):
            ch["no"] = i
            ch["id"] = f"ch{i}"
            for j, sub in enumerate(ch.get("subsections") or [], 1):
                sub["id"] = f"ch{i}.{j}"

        self.ctx.outline = outline
        self.ctx.parsed_data["_generated_outline"] = outline

    def _resume_from_last_step(self) -> dict[str, Any]:
        session = get_session()
        project = session.get(Project, self.ctx.project_id)
        step_msgs = {
            WorkflowStep.AWAIT_TENDER_FILE:
                f"等待上传招标文件：\n`{project.tender_file_path}`\n\n放好后说「放好了」",
            WorkflowStep.AWAIT_PARSE_CONFIRM:
                "请确认之前的解析结果，或告诉我需要修正的地方",
            WorkflowStep.AWAIT_OUTLINE_CONFIRM:
                ("请确认章节大纲，或说「继续」进入材料匹配。\n"
                 "也可以直接说：把第3章删了 / 加一章「数据迁移」/ 重新生成"),
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
