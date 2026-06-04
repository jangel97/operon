from __future__ import annotations

import json
import urllib.request
import urllib.error


def execute(action: str, params: dict) -> str:
    if action != "send_message":
        return f"Unknown action: {action}"

    text = params.get("text")
    if not text:
        return "Error: missing required parameter 'text'"

    token = params.get("bot_token")
    chat_id = params.get("chat_id")
    if not token or not chat_id:
        return "Error: bot_token and chat_id must be provided via tool config"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode()

    try:
        req = urllib.request.Request(
            url, data=payload, headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
    except urllib.error.URLError as e:
        return f"Error sending message: {e}"

    if result.get("ok"):
        return f"Message sent to chat {chat_id}"
    return f"Telegram API error: {result.get('description', 'unknown error')}"
