from __future__ import annotations

from operon.agent.redact import PLACEHOLDER, Redactor


class TestNoSecrets:
    def test_string_passthrough(self):
        r = Redactor()
        assert r.redact("hello world") == "hello world"

    def test_dict_passthrough(self):
        r = Redactor()
        data = {"key": "value", "nested": {"a": 1}}
        assert r.redact(data) == data

    def test_list_passthrough(self):
        r = Redactor()
        data = ["a", "b", "c"]
        assert r.redact(data) == data


class TestStringRedaction:
    def test_exact_match(self):
        r = Redactor()
        r.add_secret("supersecret")
        assert r.redact("supersecret") == PLACEHOLDER

    def test_embedded_in_text(self):
        r = Redactor()
        r.add_secret("supersecret")
        assert r.redact("the password is supersecret here") == f"the password is {PLACEHOLDER} here"

    def test_multiple_occurrences(self):
        r = Redactor()
        r.add_secret("token123")
        result = r.redact("use token123 and token123 again")
        assert result == f"use {PLACEHOLDER} and {PLACEHOLDER} again"

    def test_multiple_secrets(self):
        r = Redactor()
        r.add_secret("password1")
        r.add_secret("apikey99")
        result = r.redact("password1 and apikey99")
        assert result == f"{PLACEHOLDER} and {PLACEHOLDER}"


class TestDictRedaction:
    def test_values_redacted(self):
        r = Redactor()
        r.add_secret("s3cr3t")
        result = r.redact({"password": "s3cr3t", "user": "admin"})
        assert result == {"password": PLACEHOLDER, "user": "admin"}

    def test_keys_not_redacted(self):
        r = Redactor()
        r.add_secret("password")
        result = r.redact({"password": "safe_value"})
        assert "password" in result

    def test_nested_dict(self):
        r = Redactor()
        r.add_secret("deep_secret")
        result = r.redact({"a": {"b": {"c": "deep_secret"}}})
        assert result == {"a": {"b": {"c": PLACEHOLDER}}}


class TestListRedaction:
    def test_list_of_strings(self):
        r = Redactor()
        r.add_secret("hidden")
        result = r.redact(["visible", "hidden", "also visible"])
        assert result == ["visible", PLACEHOLDER, "also visible"]

    def test_list_of_dicts(self):
        r = Redactor()
        r.add_secret("leaked")
        result = r.redact([{"val": "leaked"}, {"val": "safe"}])
        assert result == [{"val": PLACEHOLDER}, {"val": "safe"}]


class TestNonStringValues:
    def test_int_passthrough(self):
        r = Redactor()
        r.add_secret("1234")
        assert r.redact(42) == 42

    def test_bool_passthrough(self):
        r = Redactor()
        r.add_secret("true")
        assert r.redact(True) is True

    def test_none_passthrough(self):
        r = Redactor()
        r.add_secret("none")
        assert r.redact(None) is None


class TestMinLength:
    def test_short_secret_ignored(self):
        r = Redactor()
        r.add_secret("abc")
        assert r.redact("abc is here") == "abc is here"

    def test_four_char_secret_works(self):
        r = Redactor()
        r.add_secret("abcd")
        assert r.redact("abcd is here") == f"{PLACEHOLDER} is here"

    def test_empty_secret_ignored(self):
        r = Redactor()
        r.add_secret("")
        assert r.redact("anything") == "anything"


class TestDuplicates:
    def test_duplicate_secret_not_added_twice(self):
        r = Redactor()
        r.add_secret("same")
        r.add_secret("same")
        assert len(r._secrets) == 1


class TestTraceScenario:
    def test_full_trace_event_redaction(self):
        r = Redactor()
        r.add_secret("my-api-key-12345")

        event = {
            "type": "DECISION",
            "action": "websearch:web_search",
            "params": {"query": "something with my-api-key-12345"},
            "reasoning": "I need to search for my-api-key-12345 info",
            "confidence": 0.9,
        }

        result = r.redact(event)
        assert "my-api-key-12345" not in str(result)
        assert PLACEHOLDER in result["params"]["query"]
        assert PLACEHOLDER in result["reasoning"]
        assert result["confidence"] == 0.9
        assert result["action"] == "websearch:web_search"

    def test_secret_in_result_string(self):
        r = Redactor()
        r.add_secret("db_password_xyz")

        result = r.redact("Connected with password db_password_xyz to database")
        assert "db_password_xyz" not in result
        assert PLACEHOLDER in result
