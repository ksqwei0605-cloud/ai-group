from __future__ import annotations
import asyncio
import re
import time
from typing import Optional
from dataclasses import dataclass, field

from agent import Agent, load_agents, load_config
from context_manager import ContextManager


@dataclass(order=True)
class SpeechRequest:
    priority: int
    timestamp: float = field(compare=True)
    agent_key: str = field(compare=False)
    source: str = field(compare=False)  # "rotation" or "@mention"


LOW_QUALITY_PATTERNS = [
    r"^(我同意|你说得对|有道理|没错|对的|说得好|我赞成|我支持)",
    r"^(嗯|好|对|是的)[，。]",
    r"^完全同意",
    r"^我也这么觉得",
]

TRANSITION_WORDS = r"(但是|不过|然而|补充|另外|以下是|具体来说|需要补充|我想强调的是|还有一点|除此之外|更重要的是)"


def detect_low_quality(content: str) -> tuple[bool, str]:
    """Check if a response is low-quality (empty agreement without new contribution)."""
    if len(content.strip()) < 30:
        return True, "发言过短，可能没有实质内容"

    for pattern in LOW_QUALITY_PATTERNS:
        if re.search(pattern, content.strip()):
            if not re.search(TRANSITION_WORDS, content):
                return True, f"疑似无脑附和，检测到空洞附和词但无转折补充"
    return False, ""


def parse_mentions(content: str) -> list[str]:
    role_map = {
        "架构师": "architect",
        "研究员": "researcher",
        "拆解者": "decomposer",
        "挑战者": "challenger",
        "裁决者": "arbiter",
    }
    mentions = []
    for pattern in re.finditer(r"@(\S+)", content):
        name = pattern.group(1)
        if name in role_map:
            mentions.append(role_map[name])
        else:
            for role_name, key in role_map.items():
                if role_name in name or name in role_name:
                    mentions.append(key)
                    break
    return list(dict.fromkeys(mentions))


def get_turn_prompt(agent_key: str, agents: dict[str, Agent]) -> str:
    agent = agents[agent_key]
    role_names = {
        "architect": "架构师",
        "researcher": "研究员",
        "decomposer": "拆解者",
        "challenger": "挑战者",
        "arbiter": "裁决者",
    }
    role_cn = role_names.get(agent.role, agent.name)
    return (
        f"现在轮到{role_cn}（{agent.name}）发言。"
        f"请基于前面所有人的讨论，给出你的分析和观点。"
        f"记住：禁止无脑附和，每次发言必须推进讨论。"
    )


class DebateOrchestrator:
    def __init__(self):
        self.config = load_config()
        self.agents = load_agents()
        self.context = ContextManager()
        self.queue: asyncio.PriorityQueue[SpeechRequest] = asyncio.PriorityQueue()
        self.low_quality_counts: dict[str, int] = {}
        self.stop_requested = False
        self.phase = "init"
        self.default_order = list(self.config["debate"]["phase1_order"])
        self.order_index = 0

    async def run(self, question: str, ui):
        self.context.start_debate(question)

        # Inject uploaded files as shared reference for all agents
        files_ctx = getattr(self.context, "files_context", "")
        if files_ctx:
            self.context.messages.append({
                "role": "user",
                "content": f"【主持人上传了参考文件，以下内容对所有讨论者可见】\n\n{files_ctx}",
            })

        self.phase = "structured"

        # --- Phase 1: Structured rounds (1-4) ---
        phase1_order = self.config["debate"]["phase1_order"]
        for i, agent_key in enumerate(phase1_order):
            if self.stop_requested:
                break
            await self._speak(agent_key, ui)

        # --- Phase 2: Free debate with @ queue ---
        self.phase = "free"
        free_order = self.config["debate"]["free_debate_order"]
        max_rounds = self.config["debate"]["max_rounds"]
        round_idx = 0
        quiet_rounds = 0

        while round_idx < max_rounds and not self.stop_requested:
            # Check for @ mentions in last message
            if self.context.messages:
                last_msg = self.context.messages[-1]["content"]
                mentions = parse_mentions(last_msg)
                for m_key in mentions:
                    if m_key in self.agents and m_key != self._last_speaker:
                        self.queue.put_nowait(SpeechRequest(
                            priority=self.agents[m_key].priority,
                            timestamp=time.time(),
                            agent_key=m_key,
                            source="@mention",
                        ))

            # Pick next speaker
            speaker = await self._pick_next_speaker(free_order)
            if speaker is None:
                speaker = free_order[self.order_index % len(free_order)]
                self.order_index += 1

            has_new_info = await self._speak(speaker, ui)

            if has_new_info:
                quiet_rounds = 0
            else:
                quiet_rounds += 1

            if quiet_rounds >= 3:
                await ui.show_info("检测到讨论趋于平静，自动触发总结...")
                break

            round_idx += 1
            await asyncio.sleep(1.0)

        # --- Arbiter summary ---
        await self._arbiter_summary(ui)

        # --- Persist ---
        filepath = self.context.save()
        await ui.show_info(f"辩论记录已保存至: {filepath}")

    async def _speak(self, agent_key: str, ui) -> bool:
        agent = self.agents[agent_key]
        self._last_speaker = agent_key

        await ui.show_thinking(agent.name, agent.color)

        messages = self.context.get_context_for_agent(agent.name)

        try:
            response = await agent.respond(messages)
        except Exception as e:
            error_msg = f"[API 调用失败: {e}]"
            await ui.show_info(f"  ✗ {agent.name} API 错误：{e}")
            self.context.add_agent_message(agent_key, agent.name, error_msg, "error")
            return False

        is_low, reason = detect_low_quality(response)
        if is_low:
            await ui.show_low_quality_warning(agent.name, reason)
            self.low_quality_counts[agent_key] = self.low_quality_counts.get(agent_key, 0) + 1

            if self.low_quality_counts.get(agent_key, 0) < 2:
                retry_messages = messages + [
                    {"role": "assistant", "content": response},
                    {"role": "user", "content": (
                        f"你的上一条回复被判定为低质量（原因：{reason}）。"
                        f"请认真思考后重新发言。记住：禁止无脑附和，每次发言必须带来新信息、"
                        f"新视角，或者具体的反对意见+替代方案。"
                    )},
                ]
                response = await agent.respond(retry_messages)
                is_low2, _ = detect_low_quality(response)
                if is_low2:
                    await ui.show_info(f"{agent.name} 连续低质量发言，跳过本轮")
                    self.context.add_agent_message(agent_key, agent.name, "[本轮发言被跳过：连续低质量]", "skipped")
                    return False

        self.context.add_agent_message(agent_key, agent.name, response, "low" if is_low else "good")
        await ui.show_speech(agent.name, agent.role, agent.color, response)
        return not is_low

    async def _pick_next_speaker(self, free_order: list) -> Optional[str]:
        try:
            request = self.queue.get_nowait()
            return request.agent_key
        except asyncio.QueueEmpty:
            return None

    async def _arbiter_summary(self, ui):
        if "arbiter" not in self.agents:
            await ui.show_info("未配置裁决者，跳过总结")
            return

        agent = self.agents["arbiter"]
        await ui.show_info("━" * 50)
        await ui.show_thinking(agent.name, agent.color)

        summary_prompt = self.context.messages + [{
            "role": "user",
            "content": (
                "现在轮到你——裁决者——进行最终总结。\n\n"
                "请综合以上所有讨论，输出一份结构化的最终执行计划。\n"
                "格式要求：\n"
                "## 一、目标概述\n"
                "## 二、技术方案（说明为什么选择这个路线，讨论中哪些方案被淘汰及其原因）\n"
                "## 三、执行步骤（按顺序编号，标注前置依赖）\n"
                "## 四、风险点与应对\n"
                "## 五、备选方案（如果主方案失败）\n"
                "## 六、未解决的争议（如果有）"
            ),
        }]
        response = await agent.respond(summary_prompt)
        self.context.set_final_plan(response, "裁决者总结")
        await ui.show_speech(agent.name, agent.role, agent.color, response)
        await ui.show_info("━" * 50)
        await ui.show_info("辩论结束。以上方案可以交给 Claude Code 执行。")
