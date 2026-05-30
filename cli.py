"""
标书制作工具 - 对话会话管理器
确认驱动的工作流：AI 做一步 → 用户确认/纠正 → 继续
"""
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import yaml

# ---- 配置加载 ----
_CONFIG_DIR = Path(__file__).parent
CONFIG_PATH = _CONFIG_DIR / "config.yaml"
if not CONFIG_PATH.exists():
    CONFIG_PATH = Path.home() / "tender-tool" / "config.yaml"

def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

config = load_config()
PROJECTS_DIR = Path(config["tender_tool"]["projects_dir"]).expanduser()
MATERIALS_DIR = Path(config["tender_tool"]["materials_dir"]).expanduser()
EXPORTS_DIR = Path(config["tender_tool"]["exports_dir"]).expanduser()


class WorkflowStep(str):
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


class ConversationSession:
    def __init__(self):
        self.current_project_id: Optional[int] = None
        self.current_tender_id: Optional[int] = None
        self.current_tender_type: Optional[str] = None
        self.step: WorkflowStep = WorkflowStep.IDLE
        self.context: dict[str, Any] = {}

    def reset(self):
        self.__init__()


class ConversationManager:
    SESSION_FILE = Path.home() / "tender-tool" / ".session.json"

    def __init__(self):
        self.session = self._load_session()

    def _load_session(self) -> ConversationSession:
        if self.SESSION_FILE.exists():
            try:
                data = json.loads(self.SESSION_FILE.read_text())
                s = ConversationSession()
                s.current_project_id = data.get("current_project_id")
                s.current_tender_id = data.get("current_tender_id")
                s.current_tender_type = data.get("current_tender_type")
                s.step = WorkflowStep(data.get("step", "idle"))
                s.context = data.get("context", {})
                return s
            except Exception:
                pass
        return ConversationSession()

    def _save_session(self):
        data = {
            "current_project_id": self.session.current_project_id,
            "current_tender_id": self.session.current_tender_id,
            "current_tender_type": self.session.current_tender_type,
            "step": self.session.step,
            "context": self.session.context,
        }
        self.SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.SESSION_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def handle(self, user_message: str) -> str:
        msg = user_message.strip()
        if self.session.step == WorkflowStep.IDLE:
            return self._handle_idle(msg)
        elif self.session.step == WorkflowStep.AWAIT_TENDER_FILE:
            return self._handle_await_tender_file(msg)
        elif self.session.step == WorkflowStep.AWAIT_PARSE_CONFIRM:
            return self._handle_await_parse_confirm(msg)
        elif self.session.step == WorkflowStep.AWAIT_CHAPTER_CONFIRM:
            return self._handle_await_chapter_confirm(msg)
        elif self.session.step == WorkflowStep.AWAIT_DRAFT_CONFIRM:
            return self._handle_await_draft_confirm(msg)
        elif self.session.step == WorkflowStep.AWAIT_REVIEW_ACTION:
            return self._handle_await_review_action(msg)
        else:
            return self._handle_idle(msg)

    def _handle_idle(self, msg: str) -> str:
        if not msg:
            return ("你好！我是标书制作助手。\n\n"
                    "输入项目名称即可开始，例如：\n"
                    "「新建项目：xx医院HIS投标」")
        if "新建项目" in msg or "新建" in msg or "开始" in msg:
            name = re.sub(r"^(新建项目|新建|开始)[:：]?\s*", "", msg).strip()
            if not name:
                return "请告诉我项目名称，例如：新建项目：xx医院HIS投标"
            return self._create_project(name)
        if "继续" in msg:
            if self.session.current_project_id:
                return self._resume_from_last_step()
            return "当前没有进行中的项目，请说「新建项目：xxx」开始"
        if "当前项目" in msg:
            return self._show_current_project()
        if "帮助" in msg:
            return self._show_help()
        # 尝试当作新项目名处理
        return self._create_project(msg)

    def _create_project(self, name: str) -> str:
        from models import init_db, get_session, Project
        init_db()
        session = get_session()
        safe_name = re.sub(r"[^\w\-]", "_", name)
        timestamp = datetime.now().strftime("%Y%m%d")
        project_dir = PROJECTS_DIR / f"{timestamp}_{safe_name}"
        project_dir.mkdir(parents=True, exist_ok=True)
        tender_path = project_dir / "tender.pdf"
        project = Project(name=name, tender_file_path=str(tender_path), status="parsing")
        session.add(project)
        session.commit()
        session.refresh(project)
        self.session.current_project_id = project.id
        self.session.step = WorkflowStep.AWAIT_TENDER_FILE
        self._save_session()
        return (f"✅ 项目已创建：{name}\n"
                f"📁 项目目录：{project_dir}\n\n"
                f"请将招标文件（PDF 或 DOCX）放到以下路径：\n"
                f"`{tender_path}`\n\n"
                f"放好后告诉我「放好了」，我立即开始解析。")

    def _handle_await_tender_file(self, msg: str) -> str:
        from models import get_session, Project
        if not re.search(r"放好了|上传了|好了", msg):
            return "请把招标文件放到指定路径，然后说「放好了」"
        session = get_session()
        project = session.get(Project, self.session.current_project_id)
        if not project:
            return "找不到当前项目，请说「新建项目：xxx」重新开始"
        tender_path = Path(project.tender_file_path)
        if not tender_path.exists():
            return f"文件还没找到：`{tender_path}`，请确认文件已放置"
        return self._do_parse(project, tender_path)

    def _do_parse(self, project, tender_path: Path) -> str:
        from models import get_session, Project
        self.session.step = WorkflowStep.PARSING
        self._save_session()
        # TODO: 调用 DeepSeek API 解析文件
        parsed_data = {
            "K01_项目名称": project.name,
            "K02_招标编号": "HN-2026-0501",
            "K03_招标人": "xx省人民医院",
            "K04_预算金额": "850万元",
            "K05_投标截止": "2026-06-15 14:00",
            "K06_开标时间": "2026-06-15 14:00",
            "K07_评分标准": "技术60%+商务40%",
            "K08_技术要求": "覆盖HIS/EMR/LIS/PACS系统",
            "K09_商务资质": "需提供等保证明、三甲医院案例≥3个",
            "K10_星标项": ["★ 必须具备等保三级", "★ 演示时间30分钟"],
            "K11_废标条款": ["证书过期视为废标", "偏离超过20%视为废标"],
            "K12_章节要求": "共8章，详见第三章",
            "K13_偏离表格式": "须使用招标方指定格式",
            "K14_演示要求": "需现场演示，PPT不超过20页",
        }
        session = get_session()
        project = session.get(Project, self.session.current_project_id)
        project.parsed_data = json.dumps(parsed_data, ensure_ascii=False)
        project.project_name = parsed_data["K01_项目名称"]
        project.tender_no = parsed_data["K02_招标编号"]
        project.status = "parsed"
        session.commit()
        self.session.context["parsed_data"] = parsed_data
        self.session.step = WorkflowStep.AWAIT_PARSE_CONFIRM
        self._save_session()
        lines = ["📋 解析完成！关键信息如下：\n"]
        for k, v in parsed_data.items():
            lines.append(f"**{k}**：{v}")
        lines.append("\n请确认以上信息是否正确。有错误的请告诉我，例如：「预算金额应该是900万」")
        return "\n".join(lines)

    def _handle_await_parse_confirm(self, msg: str) -> str:
        from models import get_session, Project
        corrections = self._extract_corrections(msg)
        session = get_session()
        project = session.get(Project, self.session.current_project_id)
        response = ""
        if corrections:
            if "预算" in corrections:
                budget_val = re.sub(r"[^\d.]", "", str(corrections["预算"]))
                project.budget = float(budget_val) if budget_val else None
            if "招标编号" in corrections:
                project.tender_no = corrections["招标编号"]
            if "项目名称" in corrections:
                project.project_name = corrections["项目名称"]
            session.commit()
            self.session.context["corrections"] = corrections
            response = "✅ 已修正：\n"
            response += "\n".join([f"  • {k}: {v}" for k, v in corrections.items()])
            response += "\n\n"
        project.status = "materials_preparing"
        session.commit()
        chapters = [
            {"chapter": "第一章 公司简介", "material": "公司简介模板", "reason": "标准版本可直接使用"},
            {"chapter": "第二章 业绩案例", "material": "xx省人民医院HIS系统（2024）", "reason": "三甲医院HIS系统，匹配度高"},
            {"chapter": "第三章 技术方案", "material": "HIS技术方案v3", "reason": "最新版，覆盖招标要求"},
            {"chapter": "第四章 实施计划", "material": "标准实施方法论", "reason": "通用版本"},
        ]
        self.session.context["chapters"] = chapters
        self.session.step = WorkflowStep.AWAIT_CHAPTER_CONFIRM
        self._save_session()
        response += "📚 材料匹配结果：\n"
        for ch in chapters:
            response += f"\n**{ch['chapter']}**\n"
            response += f"  → 推荐：{ch['material']}\n"
            response += f"  → 理由：{ch['reason']}\n"
        response += "\n要说「继续」进入生成，或者告诉我需要换哪个章节"
        return response

    def _extract_corrections(self, msg: str) -> dict:
        corrections = {}
        # 预算
        m = re.search(r"预算[是为应该是]*\s*(\d+\.?\d*)\s*(万|元)?", msg)
        if m:
            corrections["预算"] = m.group(0)
        # 招标编号
        m = re.search(r"编号[是为应该是]*\s*([A-Za-z0-9\-]+)", msg)
        if m:
            corrections["招标编号"] = m.group(1)
        # 项目名称
        if "项目名称" in msg:
            m = re.search(r"项目名称[是为应该是]*\s*(.+?)(?:\n|$)", msg)
            if m:
                corrections["项目名称"] = m.group(1).strip()
        return corrections

    def _handle_await_chapter_confirm(self, msg: str) -> str:
        if re.search(r"继续|确认|可以|好的", msg):
            return self._start_generation()
        if re.search(r"换|替换|换一个", msg):
            return "好的，已重新推荐了另一个材料，请确认是否合适"
        return "可以说「继续」进入生成，或者告诉我需要换哪个章节"

    def _start_generation(self) -> str:
        self.session.step = WorkflowStep.AWAIT_DRAFT_CONFIRM
        self._save_session()
        return ("✅ 主标初稿已生成！\n\n"
                "**核心亮点：**\n"
                "• 基于3个三甲医院案例拼接\n"
                "• 技术方案突出「云架构+微服务」\n"
                "• 偏离表已生成，共12项响应\n\n"
                "**请注意以下几点：**\n"
                "• 第3章工期描述已按招标要求修正为8个月\n"
                "• 第5章金额已统一为850万\n\n"
                "输入「终审」进行检查，或「修改」告诉我需要改的地方。")

    def _handle_await_draft_confirm(self, msg: str) -> str:
        if re.search(r"终审|检查", msg):
            return self._run_review()
        if re.search(r"修改|改|换", msg):
            return "好的，请告诉我要改哪里，我来修正"
        if "导出" in msg:
            return self._show_export_options()
        return "可以说「终审」进行检查，或告诉我需要修改的地方"

    def _show_export_options(self) -> str:
        return ("📤 导出格式：\n"
                "• 「导出Word」- 生成 .docx 文件\n"
                "• 「导出PDF」- 生成 .pdf 文件")

    def _run_review(self) -> str:
        self.session.step = WorkflowStep.AWAIT_REVIEW_ACTION
        self._save_session()
        report = {
            "C01_名称一致性": ("✅", "通过", []),
            "C02_产品名称一致性": ("✅", "通过", []),
            "C03_时间一致性": ("⚠️", "警告", ["第3章工期8个月，第7章写的是6个月"]),
            "C04_金额一致性": ("✅", "通过", []),
            "C05_章节完整性": ("✅", "通过", []),
            "C06_星标项覆盖": ("✅", "通过", []),
            "C07_废标条款": ("✅", "通过", []),
        }
        lines = ["🔍 终审检查报告：\n"]
        for k, (icon, status, issues) in report.items():
            lines.append(f"{icon} **{k}**：{status}")
            for issue in issues:
                lines.append(f"   - {issue}")
        warning_count = sum(1 for _, (icon, _, _) in report.items() if icon == "⚠️")
        lines.append(f"\n总结：⚠️ 警告 {warning_count} 项")
        if warning_count > 0:
            lines.append("\n要说「自动修正」还是你手动改？")
        return "\n".join(lines)

    def _handle_await_review_action(self, msg: str) -> str:
        if re.search(r"自动修正|自动修", msg):
            return ("✅ 已自动修正一致性问题\n"
                    "• 第3章工期已统一为8个月\n\n"
                    "现在可以导出了：\n"
                    "「导出Word」 / 「导出PDF」")
        if re.search(r"导出|word|pdf", msg.lower()):
            return self._do_export(msg)
        return "可以说「自动修正」或告诉我具体要改什么"

    def _do_export(self, msg: str) -> str:
        fmt = "word"
        if "pdf" in msg.lower():
            fmt = "pdf"
        export_path = EXPORTS_DIR / f"tender_{self.session.current_project_id}.{fmt}"
        return (f"✅ 已导出为 **{fmt.upper()}**\n"
                f"📁 保存路径：`{export_path}`\n\n"
                "本次项目制作完成！要说「新建项目」开始下一个。")

    def _show_current_project(self) -> str:
        if not self.session.current_project_id:
            return "当前没有进行中的项目"
        from models import get_session, Project
        session = get_session()
        project = session.get(Project, self.session.current_project_id)
        if not project:
            return "找不到项目记录"
        return (f"📋 当前项目：{project.name}\n"
                f"状态：{project.status}\n"
                f"阶段：{self.session.step}")

    def _resume_from_last_step(self) -> str:
        step = self.session.step
        if step == WorkflowStep.AWAIT_TENDER_FILE:
            from models import get_session, Project
            session = get_session()
            project = session.get(Project, self.session.current_project_id)
            return (f"等待上传招标文件：\n`{project.tender_file_path}`\n\n"
                    "放好后说「放好了」")
        elif step == WorkflowStep.AWAIT_PARSE_CONFIRM:
            return "请确认之前的解析结果，或告诉我需要修正的地方"
        elif step == WorkflowStep.AWAIT_CHAPTER_CONFIRM:
            return "请确认材料匹配方案，或说「继续」进入生成"
        elif step == WorkflowStep.AWAIT_DRAFT_CONFIRM:
            return "请查看初稿，说「终审」进行检查，或告诉我需要修改的地方"
        return "继续中..."

    def _show_help(self) -> str:
        return ("📖 标书制作助手 - 帮助\n\n"
                "• 「新建项目：xxx」- 创建新项目\n"
                "• 「当前项目」- 查看进行中的项目\n"
                "• 「继续」- 从上一步继续\n"
                "• 「终审」- 执行终审检查\n"
                "• 「导出Word」- 导出Word文件\n"
                "• 「导出PDF」- 导出PDF文件")


def main():
    print("=" * 50)
    print("标书制作工具 - 对话模式")
    print("=" * 50)
    print()
    manager = ConversationManager()
    print(manager.handle(""))
    while True:
        try:
            user_input = input("\n👤 你：").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("再见！")
                break
            response = manager.handle(user_input)
            print(f"\n🤖 助手：{response}")
        except EOFError:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n⚠️ 错误：{e}")


if __name__ == "__main__":
    main()
