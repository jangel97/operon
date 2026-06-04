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


_ROUTER_PROMPT = (
    "You are an action router. Given a goal, available actions, and execution history, "
    "select ONLY the actions that are relevant for the NEXT step.\n\n"
    "Respond with ONLY a JSON object:\n"
    '{"actions": ["action_name_1", "action_name_2"]}\n\n'
    "Rules:\n"
    "- Select 1-5 most relevant actions for the immediate next step\n"
    "- Consider the goal and what has already been done in history\n"
    "- Include a 'done-like' action if the task might be complete\n"
    "- Output ONLY valid JSON, no markdown, no explanation\n"
)


_EXTRACTOR_PROMPT = (
    "You are a JSON extraction assistant. "
    "Given the user's raw text, extract and return ONLY a valid JSON object "
    "matching one of these two schemas:\n\n"
    "Action:\n"
    '{"done": false, "action": "<name>", "params": {...}, '
    '"reasoning": "why this action is needed", "confidence": 0.0-1.0}\n\n'
    "Done:\n"
    '{"done": true, "summary": "what was accomplished"}\n\n'
    "Rules:\n"
    "- Output ONLY valid JSON, no markdown, no explanation\n"
    "- Preserve all information from the raw text\n"
    "- If the text indicates the task is complete, use the done schema\n"
    "- If the text indicates an action to take, use the action schema\n"
)


class LLMProvider(ABC):
    _extractor: LLMProvider | None = None
    _router: LLMProvider | None = None

    def set_extractor(self, extractor: LLMProvider) -> None:
        self._extractor = extractor

    def set_router(self, router: LLMProvider) -> None:
        self._router = router

    def decide(self, goal: str, tools: list[dict], history: list[dict]) -> Decision:
        if self._router is not None:
            tools = self._route_actions(goal, tools, history)
        messages = self._build_messages(goal, tools, history)
        raw = self._call_llm(messages)
        if self._extractor is not None:
            raw = self._extract_with_model(raw)
        return self._parse_response(raw)

    def _extract_with_model(self, raw: str) -> str:
        messages = [
            {"role": "system", "content": _EXTRACTOR_PROMPT},
            {"role": "user", "content": raw},
        ]
        return self._extractor._call_llm(messages)

    def _route_actions(self, goal: str, tools: list[dict], history: list[dict]) -> list[dict]:
        action_summary = "\n".join(
            f"- {t['name']}: {t.get('description', '')}" for t in tools
        )

        history_text = ""
        if history:
            history_text = "\nRecent history:\n" + "\n".join(
                f"- {h['action']} -> {h['result'][:100]}" for h in history[-3:]
            )

        messages = [
            {"role": "system", "content": _ROUTER_PROMPT},
            {"role": "user", "content": f"Goal: {goal}\n\nAvailable actions:\n{action_summary}{history_text}"},
        ]

        try:
            raw = self._router._call_llm(messages)
            data = _extract_json(raw)
            selected = set(data.get("actions", []))
            if selected:
                filtered = [t for t in tools if t["name"] in selected]
                if filtered:
                    return filtered
        except Exception:
            pass
        return tools

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
            "- You MUST use the available actions to accomplish the goal\n"
            "- Do NOT answer from your own knowledge — use actions to gather information first\n"
            "- Only use actions from the available list\n"
            "- Use the minimum number of actions needed\n"
            "- When the goal is achieved, declare done with a summary\n"
            "- If an action was denied or rejected, adapt your plan\n"
            "- confidence: 1.0 = certain this is the right action, "
            "0.5 = unsure, 0.0 = guessing\n"
            "- Respond with ONLY valid JSON, no markdown, no explanation, no thinking\n"
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

        if "action" not in data:
            return Decision(done=True, summary=data.get("summary", str(data)))

        return Decision(
            action=Action(
                action=data["action"],
                params=data.get("params", {}),
                reasoning=data.get("reasoning", ""),
                confidence=float(data.get("confidence", 0.0)),
            )
        )


def _extract_json(text: str) -> dict:
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
