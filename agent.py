from __future__ import annotations
import os
import yaml
from dataclasses import dataclass, field
from openai import AsyncOpenAI

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


@dataclass
class AgentConfig:
    key: str
    name: str
    role: str
    model: str
    api_base: str
    api_key: str
    color: str
    priority: int = 3
    temperature: float = 0.8


class Agent:
    def __init__(self, config: AgentConfig):
        self.key = config.key
        self.name = config.name
        self.role = config.role
        self.model = config.model
        self.color = config.color
        self.priority = config.priority
        self.temperature = config.temperature

        api_key = config.api_key
        if not api_key:
            raise ValueError(
                f"API Key 未配置，Agent '{self.name}' 需要 API Key"
            )

        import httpx
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=config.api_base,
            timeout=httpx.Timeout(120.0, connect=15.0),
        )

        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        prompt_path = os.path.join(PROMPTS_DIR, f"{self.role}.txt")
        if os.path.exists(prompt_path):
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        return f"你是 {self.name}，负责{self.role}相关的讨论。"

    async def respond(self, messages: list[dict]) -> str:
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages

        kwargs = dict(
            model=self.model,
            messages=full_messages,
            temperature=self.temperature,
        )
        response = await self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        return content.strip() if content else ""


def load_agents() -> dict[str, Agent]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    agents = {}
    for key, cfg in config["agents"].items():
        agent_config = AgentConfig(
            key=key,
            name=cfg["name"],
            role=cfg["role"],
            model=cfg["model"],
            api_base=cfg["api_base"],
            api_key=cfg["api_key"],
            color=cfg["color"],
            priority=cfg.get("priority", 3),
            temperature=cfg.get("temperature", 0.8),
        )
        agents[key] = Agent(agent_config)
    return agents


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
