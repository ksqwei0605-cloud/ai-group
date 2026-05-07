from __future__ import annotations
import asyncio
import os
import sys
import threading
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

from file_handler import read_file, format_context

ROLE_LABELS = {
    "architect": "架构师",
    "researcher": "研究员",
    "decomposer": "拆解者",
    "challenger": "挑战者",
    "arbiter": "裁决者",
}


class DebateUI:
    def __init__(self):
        self.console = Console()
        self.status_text = Text("准备中...")
        self.input_buffer = []
        self._input_thread = None
        self._stop_event = threading.Event()
        self._live: Optional[Live] = None
        self.files_uploaded: list[str] = []  # accumulated file contexts

    def print_banner(self):
        self.console.print()
        self.console.print(Panel(
            Text("AI 群聊辩论室", style="bold white", justify="center"),
            subtitle="架构师 · 研究员 · 拆解者 · 挑战者 · 裁决者",
            border_style="cyan",
        ))
        self.console.print("[dim]输入 /stop 停止 | /skip 跳过 | /file <路径> 上传文件[/dim]")
        self.console.print()

    async def get_question(self) -> str:
        self.files_uploaded = []
        self.console.print("[bold yellow]👤 主持人[/bold yellow]，请输入你要讨论的问题：")
        self.console.print("   [dim]先用 /file <文件路径> 上传参考文件，再输入问题[/dim]")
        self.console.print()

        while True:
            line = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input(">>> ")
            )
            line = line.strip()

            if not line:
                if self.files_uploaded:
                    self.console.print("[dim]请输入问题（已上传文件：{}个）[/dim]".format(len(self.files_uploaded)))
                continue

            if line.startswith("/file "):
                rest = line[6:].strip()
                # Support: /file <path> or /file <path> <inline question>
                # Try to split: find a valid file path prefix
                path = rest
                question_suffix = ""
                # Walk back from end to find where the file path stops being valid
                parts = rest.rsplit(" ", 1)
                while len(parts) == 2:
                    candidate_path, suffix = parts
                    if os.path.exists(os.path.expanduser(candidate_path.strip())):
                        path = candidate_path.strip()
                        question_suffix = suffix.strip()
                        break
                    parts = candidate_path.rsplit(" ", 1)

                ok, fname, result = read_file(path)
                if ok:
                    self.files_uploaded.append(format_context(fname, result))
                    self.console.print(f"  [green]✓ 已上传: {fname}[/green]")
                    if question_suffix:
                        question = question_suffix
                        break
                else:
                    self.console.print(f"  [red]✗ {result}[/red]")
                continue

            # It's the question
            question = line
            break

        self.console.print()
        return question

    def get_uploaded_files_context(self) -> str:
        if not self.files_uploaded:
            return ""
        return "\n\n".join(self.files_uploaded)

    async def show_thinking(self, name: str, color: str):
        spinner = Text(f"💭 {name} 正在思考...", style=color)
        self.console.print(spinner)

    async def show_speech(self, name: str, role: str, color: str, content: str):
        role_cn = ROLE_LABELS.get(role, role)
        header = Text(f"━━━ {name} ({role_cn})", style=f"bold {color}")
        self.console.print(header)
        self.console.print(content)
        self.console.print()

    async def show_low_quality_warning(self, name: str, reason: str):
        self.console.print(f"  ⚠ [yellow]{name} 发言低质量：{reason}，要求重新生成...[/yellow]")

    async def show_info(self, msg: str):
        self.console.print(f"[dim]{msg}[/dim]")

    def start_input_listener(self, orchestrator):
        ui_ref = self

        def _listen():
            while not ui_ref._stop_event.is_set():
                try:
                    line = input()
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith("/file "):
                        rest = line[6:].strip()
                        path = rest
                        inline_msg = ""
                        parts = rest.rsplit(" ", 1)
                        while len(parts) == 2:
                            candidate_path, suffix = parts
                            if os.path.exists(os.path.expanduser(candidate_path.strip())):
                                path = candidate_path.strip()
                                inline_msg = suffix.strip()
                                break
                            parts = candidate_path.rsplit(" ", 1)

                        ok, fname, result = read_file(path)
                        if ok:
                            ctx = format_context(fname, result)
                            orchestrator.context.inject_interruption(ctx)
                            ui_ref.console.print(f"  [green]✓ 已上传文件到群聊: {fname}[/green]")
                            if inline_msg:
                                orchestrator.context.add_user_message(inline_msg)
                                ui_ref.console.print(f"[bold yellow]👤 主持人：[/bold yellow]{inline_msg}")
                        else:
                            ui_ref.console.print(f"  [red]✗ {result}[/red]")
                    elif line == "/stop":
                        orchestrator.stop_requested = True
                        ui_ref.console.print(
                            "[bold red]⚠ 主持人请求停止辩论，当前轮次结束后将触发总结...[/bold red]"
                        )
                    elif line == "/skip":
                        orchestrator.stop_requested = True
                        ui_ref.console.print("[yellow]跳过当前发言者...[/yellow]")
                    else:
                        orchestrator.context.add_user_message(line)
                        ui_ref.console.print(f"[bold yellow]👤 主持人：[/bold yellow]{line}")
                except (EOFError, KeyboardInterrupt):
                    orchestrator.stop_requested = True
                    break

        self._input_thread = threading.Thread(target=_listen, daemon=True)
        self._input_thread.start()

    def stop_input_listener(self):
        self._stop_event.set()
