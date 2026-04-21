# operon-tool-weather

Mock weather tool for testing and development. Returns randomized weather data — useful for validating the agent loop without external dependencies.

## Install

```bash
pip install -e tools/operon-tool-weather
```

## Actions

| Action | Description | Params |
|--------|-------------|--------|
| `get_current_weather` | Current conditions (temperature, humidity, wind) | `city` (required) |
| `get_forecast` | Multi-day forecast | `city` (required), `days` (1-5, default: 3) |
| `get_alerts` | Active weather alerts | `city` (required) |

All data is randomly generated. For real weather data, use `operon-tool-websearch` with a weather-focused goal instead.

## Example

```yaml
tools:
  - name: weather
    type: weather

policy:
  mode: autonomous
  allowed_actions:
    - weather:get_current_weather
    - weather:get_forecast
    - weather:get_alerts
```
