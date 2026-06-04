from __future__ import annotations

import json
import ssl
import urllib.request
import urllib.error


def _ssl_context() -> ssl.SSLContext:
    import certifi
    return ssl.create_default_context(cafile=certifi.where())


def execute(action: str, params: dict) -> str:
    if action != "get_weather":
        return f"Unknown action: {action}"

    city = params.get("city")
    if not city:
        return "Error: missing required parameter 'city'"

    url = f"https://wttr.in/{urllib.request.quote(city)}?format=j1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "operon/1.0"})
        with urllib.request.urlopen(req, timeout=10, context=_ssl_context()) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        return f"Error fetching weather: {e}"

    current = data.get("current_condition", [{}])[0]
    area = data.get("nearest_area", [{}])[0]
    area_name = area.get("areaName", [{}])[0].get("value", city)
    country = area.get("country", [{}])[0].get("value", "")

    temp_c = current.get("temp_C", "?")
    feels_like = current.get("FeelsLikeC", "?")
    humidity = current.get("humidity", "?")
    desc = current.get("weatherDesc", [{}])[0].get("value", "?")
    wind_kmph = current.get("windspeedKmph", "?")
    wind_dir = current.get("winddir16Point", "?")

    return (
        f"Weather in {area_name}, {country}:\n"
        f"  Condition: {desc}\n"
        f"  Temperature: {temp_c}°C (feels like {feels_like}°C)\n"
        f"  Humidity: {humidity}%\n"
        f"  Wind: {wind_kmph} km/h {wind_dir}"
    )
