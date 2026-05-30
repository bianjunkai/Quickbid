"""
标书制作工具 - CLI 对话入口
确认驱动的工作流：Agent 做一步 → 用户确认/纠正 → 继续

核心逻辑委托给 Orchestrator，本文件只负责 I/O 交互。
"""
import yaml
from pathlib import Path

from orchestrator import Orchestrator

# ---- 配置加载 ----
_CONFIG_DIR = Path(__file__).parent
CONFIG_PATH = _CONFIG_DIR / "config.yaml"
if not CONFIG_PATH.exists():
    CONFIG_PATH = Path.home() / "tender-tool" / "config.yaml"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    orch = Orchestrator(config.get("tender_tool", {}))

    print("=" * 50)
    print("标书制作工具 - 对话模式 (v3 多 Agent)")
    print("=" * 50)
    print()

    # 初始问候
    result = orch.handle("")
    print(f"🤖 助手：{result['message']}")

    while True:
        try:
            user_input = input("\n👤 你：").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "q"]:
                print("再见！")
                break

            result = orch.handle(user_input)
            if "message" in result:
                print(f"\n🤖 助手：{result['message']}")
            else:
                print(f"\n🤖 助手：{result}")

        except EOFError:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n⚠️ 错误：{e}")


if __name__ == "__main__":
    main()
