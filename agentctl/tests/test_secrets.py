from __future__ import annotations

import os

import pytest

from operon.agent.secrets import resolve_env_vars


class TestEnvVarResolution:
    def test_simple_var(self, monkeypatch):
        monkeypatch.setenv("MY_URL", "http://localhost:11434")
        assert resolve_env_vars("${MY_URL}") == "http://localhost:11434"

    def test_var_in_context(self, monkeypatch):
        monkeypatch.setenv("HOST", "192.168.1.137")
        result = resolve_env_vars("base_url: http://${HOST}:11434/v1")
        assert result == "base_url: http://192.168.1.137:11434/v1"

    def test_multiple_vars(self, monkeypatch):
        monkeypatch.setenv("HOST", "myhost")
        monkeypatch.setenv("PORT", "8080")
        result = resolve_env_vars("${HOST}:${PORT}")
        assert result == "myhost:8080"

    def test_var_with_default(self, monkeypatch):
        monkeypatch.delenv("MISSING_VAR", raising=False)
        result = resolve_env_vars("${MISSING_VAR:-fallback_value}")
        assert result == "fallback_value"

    def test_var_with_default_when_set(self, monkeypatch):
        monkeypatch.setenv("SET_VAR", "real_value")
        result = resolve_env_vars("${SET_VAR:-fallback}")
        assert result == "real_value"

    def test_empty_default(self, monkeypatch):
        monkeypatch.delenv("UNSET", raising=False)
        result = resolve_env_vars("${UNSET:-}")
        assert result == ""

    def test_missing_var_raises(self, monkeypatch):
        monkeypatch.delenv("DOES_NOT_EXIST", raising=False)
        with pytest.raises(ValueError, match="Environment variable not set"):
            resolve_env_vars("${DOES_NOT_EXIST}")

    def test_no_vars_passthrough(self):
        text = "base_url: http://localhost:11434/v1"
        assert resolve_env_vars(text) == text

    def test_dollar_without_braces_passthrough(self):
        text = "price is $100"
        assert resolve_env_vars(text) == text


class TestYamlIntegration:
    def test_full_yaml_interpolation(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "192.168.1.137")
        monkeypatch.setenv("DB_PASSWORD", "s3cr3t")

        yaml_text = """
spec:
  decision:
    base_url: http://${OLLAMA_HOST}:11434/v1
  inputs:
    password:
      type: string
      default: "${DB_PASSWORD}"
      no_log: true
"""
        result = resolve_env_vars(yaml_text)
        assert "192.168.1.137" in result
        assert "s3cr3t" in result
        assert "${OLLAMA_HOST}" not in result
        assert "${DB_PASSWORD}" not in result

    def test_default_in_yaml(self, monkeypatch):
        monkeypatch.delenv("OPTIONAL_VAR", raising=False)
        yaml_text = "value: ${OPTIONAL_VAR:-default_model}"
        result = resolve_env_vars(yaml_text)
        assert result == "value: default_model"


class TestEdgeCases:
    def test_var_with_spaces_in_name(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "trimmed")
        result = resolve_env_vars("${ MY_VAR }")
        assert result == "trimmed"

    def test_nested_braces_not_supported(self, monkeypatch):
        monkeypatch.setenv("A", "val")
        result = resolve_env_vars("${A}")
        assert result == "val"

    def test_consecutive_vars(self, monkeypatch):
        monkeypatch.setenv("A", "hello")
        monkeypatch.setenv("B", "world")
        assert resolve_env_vars("${A}${B}") == "helloworld"
