from __future__ import annotations
import asyncio
import sys
import io

# Fix Windows GBK encoding issue
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from orchestrator import DebateOrchestrator
from ui import DebateUI


async def main():
    ui = DebateUI()
    ui.print_banner()

    orchestrator = DebateOrchestrator()

    # Show configured agents
    for key, agent in orchestrator.agents.items():
        ui.console.print(f"  [{agent.color}]✓ {agent.name}[/{agent.color}] — {agent.model}")

    ui.console.print()

    question = await ui.get_question()
    if not question.strip():
        ui.console.print("[red]问题不能为空，退出[/red]")
        return

    # Inject uploaded files into the initial context
    files_context = ui.get_uploaded_files_context()
    if files_context:
        orchestrator.context.files_context = files_context

    ui.start_input_listener(orchestrator)

    try:
        await orchestrator.run(question, ui)
    except KeyboardInterrupt:
        ui.console.print("\n[red]辩论被中断[/red]")
    except Exception as e:
        ui.console.print(f"\n[red]错误: {e}[/red]")
        raise
    finally:
        ui.stop_input_listener()


if __name__ == "__main__":
    asyncio.run(main())
