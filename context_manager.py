from __future__ import annotations
import json
import os
import re
from datetime import datetime
from dataclasses import dataclass, field

DEBATES_DIR = os.path.join(os.path.dirname(__file__), "debates")


@dataclass
class RoundRecord:
    round_num: int
    agent_key: str
    agent_name: str
    content: str
    quality: str = "good"


@dataclass
class DebateRecord:
    timestamp: str
    question: str
    rounds: list[RoundRecord] = field(default_factory=list)
    final_plan: str = ""
    stop_reason: str = ""


class ContextManager:
    def __init__(self):
        self.messages: list[dict] = []
        self.record = DebateRecord(
            timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            question="",
        )
        self.round_count = 0

    def start_debate(self, question: str):
        self.messages = [
            {
                "role": "user",
                "content": (
                    f"【主持人】发起讨论，请大家认真分析以下问题，各司其职，"
                    f"展开深入辩论。注意：禁止无脑附和，每次发言必须推进讨论。\n\n"
                    f"问题：{question}"
                ),
            }
        ]
        self.record = DebateRecord(
            timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            question=question,
        )
        self.round_count = 0

    def add_agent_message(self, agent_key: str, agent_name: str, content: str, quality: str = "good"):
        self.round_count += 1
        self.messages.append({
            "role": "assistant",
            "content": f"【{agent_name}】{content}",
        })
        self.record.rounds.append(RoundRecord(
            round_num=self.round_count,
            agent_key=agent_key,
            agent_name=agent_name,
            content=content,
            quality=quality,
        ))

    def get_context_for_agent(self, role: str) -> list[dict]:
        current_turn = {
            "role": "user",
            "content": f"现在轮到{role}发言。请基于前面的讨论，给出你的分析和观点。",
        }
        return self.messages + [current_turn]

    def add_user_message(self, content: str):
        self.messages.append({
            "role": "user",
            "content": f"【主持人】{content}",
        })

    def inject_interruption(self, content: str):
        """Inject a high-priority interruption visible to all agents."""
        self.messages.append({
            "role": "user",
            "content": f"【系统中断 — 主持人上传了文件，所有人请将以下内容纳入讨论】\n{content}",
        })

    def set_final_plan(self, plan: str, stop_reason: str = "正常结束"):
        self.record.final_plan = plan
        self.record.stop_reason = stop_reason

    def save(self):
        os.makedirs(DEBATES_DIR, exist_ok=True)
        slug = re.sub(r"[^a-zA-Z0-9_一-鿿]+", "_", self.record.question)[:40]
        ts = self.record.timestamp.replace(":", "-")
        filename = f"{ts}_{slug}.json"
        filepath = os.path.join(DEBATES_DIR, filename)

        data = {
            "timestamp": self.record.timestamp,
            "question": self.record.question,
            "stop_reason": self.record.stop_reason,
            "total_rounds": len(self.record.rounds),
            "rounds": [
                {
                    "round": r.round_num,
                    "agent": r.agent_name,
                    "agent_key": r.agent_key,
                    "content": r.content,
                    "quality": r.quality,
                }
                for r in self.record.rounds
            ],
            "final_plan": self.record.final_plan,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filepath
