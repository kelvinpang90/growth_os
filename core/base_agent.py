"""
Agent 基类 — 封装 Claude API 工具调用循环
所有 Phase Agent 继承此类
"""
import json
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import anthropic

from core.config import settings
from core.logger import logger

# ── Prompt 加载工具 ───────────────────────────────────────────────────────
_PROMPTS_FILE = Path(__file__).parent.parent / "prompts" / "prompts.md"


def _load_prompt(name: str) -> str:
    """从 prompts/prompts.md 中读取指定名称的 prompt 块。"""
    text = _PROMPTS_FILE.read_text(encoding="utf-8")
    pattern = re.compile(
        r"^## " + re.escape(name) + r"\s*\n(.*?)(?=^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Prompt '{name}' not found in {_PROMPTS_FILE}")
    return match.group(1).strip()


class BaseAgent(ABC):
    """
    继承示例：
        class DiscoveryAgent(BaseAgent):
            @property
            def system_prompt(self): return "你是选品专家..."
            @property
            def tools(self): return [TOOL_A, TOOL_B]
            async def dispatch_tool(self, name, params): ...
    """

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.anthropic.api_key)
        self._history: list[dict] = []

    # ── 子类必须实现 ──────────────────────────────────────────────────────
    @property
    @abstractmethod
    def system_prompt(self) -> str: ...

    @property
    @abstractmethod
    def tools(self) -> list[dict]: ...

    @abstractmethod
    async def dispatch_tool(self, name: str, params: dict) -> Any: ...

    # ── 公开接口 ──────────────────────────────────────────────────────────
    async def run(self, user_message: str, fresh: bool = False) -> str:
        """
        执行 Agent 循环直到完成。
        fresh=True 时清空对话历史（适合定时任务）。
        """
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
        self._history = []
