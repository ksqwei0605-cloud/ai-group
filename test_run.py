import asyncio
import sys
import io

# Fix Windows GBK encoding issue
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from agent import load_agents
from orchestrator import DebateOrchestrator


class TestUI:
    """Minimal UI for automated testing - just prints to console."""

    async def show_thinking(self, name: str, color: str):
        print(f"\n[{name}] 思考中...", flush=True)

    async def show_speech(self, name: str, role: str, color: str, content: str):
        print(f"--- {name} ({role}) ---", flush=True)
        print(content, flush=True)
        print("", flush=True)

    async def show_low_quality_warning(self, name: str, reason: str):
        print(f"  [WARNING] {name}: {reason}", flush=True)

    async def show_info(self, msg: str):
        print(f"\n{msg}", flush=True)

    async def get_question(self) -> str:
        return "我想给一个百万级用户的web应用加入实时消息通知功能，应该怎么设计技术方案？请考虑可扩展性和成本。"


async def main():
    print("=" * 60)
    print("AI Group Chat Debate - Test Run")
    print("=" * 60)

    ui = TestUI()
    orchestrator = DebateOrchestrator()

    print("\nConfigured agents:")
    for key, agent in orchestrator.agents.items():
        print(f"  {agent.name} [{agent.role}] -> {agent.model}")

    question = await ui.get_question()
    print(f"\nQuestion: {question}\n")

    await orchestrator.run(question, ui)

    print("\n" + "=" * 60)
    print("Debate completed! Check debates/ folder for JSON record.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
