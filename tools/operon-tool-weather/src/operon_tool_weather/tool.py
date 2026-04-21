from __future__ import annotations

import random

from operon.tools.base import Tool


class WeatherTool(Tool):
    @property
    def name(self) -> str:
        return "weather"

    def actions(self) -> list[dict]:
        return [
            {
                "name": "get_current_weather",
                "description": "Get current weather conditions for a city",
                "params": {"city": "string"},
            },
            {
                "name": "get_forecast",
                "description": "Get weather forecast for a city for the next N days",
                "params": {"city": "string", "days": "integer (1-5)"},
            },
            {
                "name": "get_alerts",
                "description": "Get active weather alerts for a city",
                "params": {"city": "string"},
            },
        ]

    def execute(self, action: str, params: dict) -> str:
        city = params.get("city", "Unknown")

        if action == "get_current_weather":
            temp = random.randint(15, 35)
            humidity = random.randint(30, 90)
            conditions = random.choice(["Sunny", "Partly Cloudy", "Overcast", "Light Rain", "Thunderstorm"])
            wind = random.randint(5, 40)
            return (
                f"Current weather in {city}:\n"
                f"  Condition:   {conditions}\n"
                f"  Temperature: {temp}°C\n"
                f"  Humidity:    {humidity}%\n"
                f"  Wind:        {wind} km/h"
            )

        if action == "get_forecast":
            try:
                days = int(params.get("days", 3))
            except (ValueError, TypeError):
                days = 3
            lines = [f"Forecast for {city} ({days} days):"]
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for i in range(days):
                high = random.randint(20, 38)
                low = high - random.randint(5, 12)
                cond = random.choice(["Sunny", "Cloudy", "Rain", "Storms", "Partly Cloudy"])
                rain = random.randint(0, 100) if "Rain" in cond or "Storm" in cond else random.randint(0, 20)
                lines.append(f"  {day_names[i % 7]}: {low}-{high}°C  {cond}  (rain: {rain}%)")
            return "\n".join(lines)

        if action == "get_alerts":
            has_alert = random.choice([True, False])
            if has_alert:
                alert = random.choice([
                    "Heat advisory: temperatures expected above 38°C",
                    "Thunderstorm warning: severe storms expected this evening",
                    "Wind advisory: gusts up to 70 km/h expected",
                    "Flash flood watch: heavy rainfall expected",
                ])
                return f"Active alerts for {city}:\n  ⚠ {alert}"
            return f"No active weather alerts for {city}."

        return f"Unknown action: {action}"
