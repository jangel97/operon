from __future__ import annotations

import json
import random
import ssl
import urllib.parse
import urllib.request
import urllib.error

_current_question: dict | None = None


def _ssl_context() -> ssl.SSLContext:
    import certifi
    return ssl.create_default_context(cafile=certifi.where())


def _fetch_question(difficulty: str) -> dict:
    url = f"https://opentdb.com/api.php?amount=1&type=multiple&difficulty={difficulty}&encode=url3986"
    req = urllib.request.Request(url, headers={"User-Agent": "operon/1.0"})
    with urllib.request.urlopen(req, timeout=10, context=_ssl_context()) as resp:
        data = json.loads(resp.read())
    if data["response_code"] != 0 or not data["results"]:
        raise RuntimeError(f"API error: response_code={data['response_code']}")
    return data["results"][0]


def _decode(s: str) -> str:
    return urllib.parse.unquote(s)


def execute(action: str, params: dict) -> str:
    global _current_question

    if action == "get_question":
        difficulty = params.get("difficulty", "medium")
        try:
            q = _fetch_question(difficulty)
        except (urllib.error.URLError, RuntimeError) as e:
            return f"Error fetching question: {e}"

        choices = [_decode(q["correct_answer"])] + [_decode(a) for a in q["incorrect_answers"]]
        random.shuffle(choices)

        letter_map = {chr(65 + i): c for i, c in enumerate(choices)}
        _current_question = {
            "correct": _decode(q["correct_answer"]),
            "category": _decode(q["category"]),
            "difficulty": q["difficulty"],
            "letter_map": letter_map,
        }

        labeled = [f"  {chr(65 + i)}. {c}" for i, c in enumerate(choices)]
        return (
            f"Category: {_current_question['category']}\n"
            f"Difficulty: {_current_question['difficulty']}\n"
            f"Question: {_decode(q['question'])}\n"
            f"Options:\n" + "\n".join(labeled)
        )

    if action == "answer_question":
        if not _current_question:
            return "Error: no active question. Use get_question first."

        raw_answer = params.get("answer", "").strip()
        correct = _current_question["correct"]
        letter_map = _current_question.get("letter_map", {})
        _current_question = None

        answer = letter_map.get(raw_answer.upper(), raw_answer)

        if answer.lower() == correct.lower():
            return f"Correct! The answer is: {correct}"
        return f"Wrong. You answered: {answer}. The correct answer was: {correct}"

    return f"Unknown action: {action}"
