import pytest
from google.genai import errors

import llm_client
from llm_client import GeminiJsonClient


class Response:
    def __init__(self, text):
        self.text = text


class Models:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return Response(value)


class Client:
    def __init__(self, responses):
        self.models = Models(responses)


class ClientFactory:
    def __init__(self, clients):
        self.clients = clients
        self.api_keys = []

    def __call__(self, api_key):
        self.api_keys.append(api_key)
        return self.clients[api_key]


def test_generate_json_requests_gemini_structured_output():
    client = Client(['{"is_recent": true}'])
    schema = {
        "type": "object",
        "properties": {"is_recent": {"type": "boolean"}},
        "required": ["is_recent"],
    }

    result = GeminiJsonClient(client=client, model="gemini-2.5-flash").generate_json(
        "check article",
        schema,
        temperature=0.0,
    )

    assert result == {"is_recent": True}
    call = client.models.calls[0]
    assert call["model"] == "gemini-2.5-flash"
    assert call["contents"] == "check article"
    assert call["config"]["temperature"] == 0.0
    assert call["config"]["response_mime_type"] == "application/json"
    assert call["config"]["response_json_schema"] == schema


def test_generate_json_retries_transient_generation_failure():
    client = Client([RuntimeError("temporary"), '{"value": 7}'])
    sleeps = []
    gemini = GeminiJsonClient(client=client, sleep=sleeps.append)

    result = gemini.generate_json(
        "retry",
        {
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
        },
    )

    assert result == {"value": 7}
    assert len(client.models.calls) == 2
    assert sleeps == [1]


def test_generate_json_retries_gemini_api_failure():
    client = Client(
        [errors.ServerError(503, {"message": "temporary"}), '{"value": 7}']
    )
    sleeps = []
    gemini = GeminiJsonClient(client=client, sleep=sleeps.append)

    result = gemini.generate_json("retry", {"type": "object"})

    assert result == {"value": 7}
    assert len(client.models.calls) == 2
    assert sleeps == [1]


def test_generate_json_does_not_retry_permanent_gemini_api_failure():
    client = Client([errors.ClientError(400, {"message": "bad"})])
    sleeps = []
    gemini = GeminiJsonClient(client=client, sleep=sleeps.append)

    with pytest.raises(RuntimeError, match="Gemini JSON generation failed"):
        gemini.generate_json("retry", {"type": "object"})

    assert len(client.models.calls) == 1
    assert sleeps == []


def test_generate_json_fails_after_invalid_json_responses():
    client = Client(["not json", "still not json", "bad"])
    gemini = GeminiJsonClient(
        client=client,
        sleep=lambda seconds: None,
    )

    with pytest.raises(RuntimeError, match="Gemini JSON generation failed"):
        gemini.generate_json("invalid", {"type": "object"})

    assert len(client.models.calls) == 3


def test_client_requires_gemini_api_key_without_injected_client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEYS", raising=False)

    with pytest.raises(KeyError, match="GEMINI_API_KEY"):
        GeminiJsonClient()


def test_client_reads_model_from_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-custom")

    gemini = GeminiJsonClient(client=Client([]))

    assert gemini.model == "gemini-custom"


def test_client_reads_multiple_api_keys_from_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEYS", " key-one, key-two ,, ")
    factory = ClientFactory(
        {
            "key-one": Client(['{"value": 1}']),
            "key-two": Client(['{"value": 2}']),
        }
    )

    gemini = GeminiJsonClient(client_factory=factory)

    assert gemini.generate_json("first", {"type": "object"}) == {"value": 1}
    assert gemini.generate_json("second", {"type": "object"}) == {"value": 2}
    assert factory.api_keys == ["key-one", "key-two"]


def test_generate_json_tries_next_api_key_after_quota_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEYS", "quota-key,backup-key")
    factory = ClientFactory(
        {
            "quota-key": Client([errors.ClientError(429, {"message": "quota"})]),
            "backup-key": Client(['{"value": 7}']),
        }
    )
    sleeps = []
    gemini = GeminiJsonClient(client_factory=factory, sleep=sleeps.append)

    assert gemini.generate_json("retry", {"type": "object"}) == {"value": 7}
    assert factory.api_keys == ["quota-key", "backup-key"]
    assert sleeps == []


def test_module_generate_json_uses_default_client(monkeypatch):
    instances = []

    class FakeGeminiJsonClient:
        def __init__(self):
            self.calls = []
            instances.append(self)

        def generate_json(self, prompt, response_schema, temperature=0.1):
            self.calls.append((prompt, response_schema, temperature))
            return {
                "prompt": prompt,
                "schema": response_schema,
                "temperature": temperature,
            }

    monkeypatch.setattr(llm_client, "_default_client", None, raising=False)
    monkeypatch.setattr(llm_client, "GeminiJsonClient", FakeGeminiJsonClient)

    assert llm_client.generate_json("write", {"type": "object"}, temperature=0.0) == {
        "prompt": "write",
        "schema": {"type": "object"},
        "temperature": 0.0,
    }
    assert llm_client.generate_json("again", {"type": "object"}) == {
        "prompt": "again",
        "schema": {"type": "object"},
        "temperature": 0.1,
    }
    assert len(instances) == 1
    assert instances[0].calls == [
        ("write", {"type": "object"}, 0.0),
        ("again", {"type": "object"}, 0.1),
    ]
