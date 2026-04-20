from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Action:
    action: str
    params: dict = field(default_factory=dict)
    reasoning: str = ""
    confidence: float = 0.0


@dataclass
class Decision:
    action: Action | None = None
    done: bool = False
    summary: str = ""


class LLMProvider(ABC):
    def decide(self, goal: str, tools: list[dict], history: list[dict]) -> Decision:
        messages = self._build_messages(goal, tools, history)
        raw = self._call_llm(messages)
        return self._parse_response(raw)

    @abstractmethod
    def _call_llm(self, messages: list[dict]) -> str:
        pass

    def _build_messages(self, goal: str, tools: list[dict], history: list[dict]) -> list[dict]:
        system_prompt = (
            "You are an autonomous agent executing a goal.\n\n"
            f"Goal: {goal}\n\n"
            f"Available actions:\n{json.dumps(tools, indent=2)}\n\n"
            "You MUST respond with ONLY a JSON object. Either:\n"
            "1. Choose an action:\n"
            "{\n"
            '  "done": false,\n'
            '  "action": "<action_name>",\n'
            '  "params": {...},\n'
            '  "reasoning": "why this action is needed",\n'
            '  "confidence": 0.0-1.0\n'
            "}\n"
            "2. Declare done:\n"
            "{\n"
            '  "done": true,\n'
            '  "summary": "what was accomplished"\n'
            "}\n\n"
            "Rules:\n"
            "- Only use actions from the available list\n"
            "- Use the minimum number of actions needed\n"
            "- When the goal is achieved, declare done\n"
            "- If an action was denied or rejected, adapt your plan\n"
            "- confidence: 1.0 = certain this is the right action, "
            "0.5 = unsure, 0.0 = guessing\n"
            "- Respond with ONLY valid JSON, no markdown, no explanation\n"
        )

        messages: list[dict] = [{"role": "system", "content": system_prompt}]

        if not history:
            messages.append({
                "role": "user",
                "content": "Begin execution. Analyze the situation and decide the first action.",
            })
        else:
            history_text = "\n".join(
                f"- {h['action']}({json.dumps(h['params'])}) -> {h['result']}"
                for h in history
            )
            messages.append({
                "role": "user",
                "content": f"Execution history:\n{history_text}\n\nDecide the next action or declare done.",
            })

        return messages

    def _parse_response(self, raw: str) -> Decision:
        data = _extract_json(raw)

        if data.get("done"):
            return Decision(done=True, summary=data.get("summary", ""))

        return Decision(
            action=Action(
                action=data["action"],
                params=data.get("params", {}),
                reasoning=data.get("reasoning", ""),
                confidence=float(data.get("confidence", 0.0)),
            )
        )


def _extract_json(text: str) -> dict:
    text = re.sub(r"<[^>]+>.*?</[^>]+>", "", text, flags=re.DOTALL).strip()

    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        return json.loads(fence.group(1))

    for match in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text):
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            continue

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"done": True, "summary": text}
