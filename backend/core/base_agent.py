"""
Agent base class — wraps the Claude API tool-use loop
All Phase Agents inherit from this class
"""
import asyncio
import json
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml

import anthropic

from core.config import settings
from core.logger import logger

# ── Prompt 加载工具 ───────────────────────────────────────────────────────
_PROMPTS_FILE = Path(__file__).parent.parent / "prompts" / "prompts.md"


def _load_prompt(name: str) -> str:
    # 从 prompts/prompts.md 中读取指定名称的 prompt 块。
    text = _PROMPTS_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^## " + re.escape(name) + r"\s*\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Prompt '{name}' not found in {_PROMPTS_FILE}")
    return match.group(1).strip()


# ── Config 加载工具 ───────────────────────────────────────────────────────
_CONFIG_FILE = Path(__file__).parent.parent / "config" / "platform_config.md"


def _load_config(name: str):
    # 从 config/platform_config.md 中读取指定名称块内的 YAML 数据。
    text = _CONFIG_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^## " + re.escape(name) + r"\s*\n```yaml\n(.*?)```",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Config '{name}' not found in {_CONFIG_FILE}")
    return yaml.safe_load(match.group(1))


class BaseAgent(ABC):
    """Abstract base class for all AI agents. Subclasses must implement system_prompt, tools, and dispatch_tool."""

    def __init__(self):
        # api_key=None 时 SDK 自动读取 ANTHROPIC_API_KEY 环境变量；
        # 传 "" 空字符串会直接报 TypeError，所以用 or None 做保险
        self._client = anthropic.Anthropic(api_key=settings.anthropic.api_key or None)
        self._history: list[dict] = []

    # ── 子类必须实现 ──────────────────────────────────────────────────────
    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @property
    @abstractmethod
    def tools(self) -> list[dict]: ...

    @property
    def tool_registry(self) -> dict:
        # 工具名称到处理方法的映射；子类通过覆盖此属性注册工具，无需重写 dispatch_tool。
        return {}

    async def dispatch_tool(self, name: str, params: dict) -> Any:
        # 从 tool_registry 查找工具处理器并调用，支持同步和异步处理器。
        handler = self.tool_registry.get(name)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        return await handler(params) if asyncio.iscoroutinefunction(handler) else handler(params)

    # ── 公开接口 ──────────────────────────────────────────────────────────
    async def run(self, user_message: str, fresh: bool = False) -> str:
        # 执行 Claude Agent 工具调用循环直到完成，fresh=True 时清空对话历史（适合定时任务）。
        if fresh:
            self._history = []

        self._history.append({"role": "user", "content": user_message})
        final_text = ""
        rounds = 0

        while rounds < 20:          # 防无限循环
            rounds += 1
            response = self._client.messages.create(
                model=settings.anthropic.model,
                max_tokens=settings.anthropic.max_tokens,
                system=self.system_prompt,
                tools=self.tools or [],
                messages=self._history,
            )

            text_parts = [b.text for b in response.content if b.type == "text"]
            if text_parts:
                final_text = "\n".join(text_parts)

            if response.stop_reason == "end_turn":
                self._history.append({"role": "assistant", "content": response.content})
                break

            if response.stop_reason == "tool_use":
                self._history.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    logger.info(f"[{self.__class__.__name__}] tool={block.name} params={json.dumps(block.input, ensure_ascii=False)[:200]}")
                    t0 = time.monotonic()
                    try:
                        result = await self.dispatch_tool(block.name, block.input)
                    except Exception as e:
                        result = {"error": str(e)}
                    ms = int((time.monotonic() - t0) * 1000)
                    logger.info(f"[{self.__class__.__name__}] tool={block.name} done in {ms}ms")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    })

                self._history.append({"role": "user", "content": tool_results})
            else:
                break

        return final_text

    def reset(self) -> None:
        # 清空对话历史，使 Agent 进入全新状态。
        self._history = []
