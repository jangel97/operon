def execute(action: str, params: dict) -> str:
    if action == "greet":
        name = params.get("name", "World")
        return f"Hello, {name}!"
    return f"Unknown action: {action}"
