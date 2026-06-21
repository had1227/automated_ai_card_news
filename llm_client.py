from __future__ import annotations

import json
import os
import time

from google import genai
from google.genai import errors


DEFAULT_MODEL = "gemini-2.5-flash"
_default_client = None


def _api_error_status(exc):
    for attr in ("code", "status_code"):
        value = getattr(exc, attr, None)
        if value is not None:
            return int(value)
    return None


def _is_retryable_api_error(exc):
    status = _api_error_status(exc)
    return status in (408, 429) or (status is not None and status >= 500)


def _env_api_keys():
    raw_keys = os.getenv("GEMINI_API_KEYS")
    if raw_keys:
        keys = [key.strip() for key in raw_keys.split(",") if key.strip()]
        if keys:
            return keys
    return [os.environ["GEMINI_API_KEY"]]


class GeminiJsonClient:
    def __init__(
        self,
        client=None,
        model=None,
        max_retries=3,
        sleep=time.sleep,
        api_keys=None,
        client_factory=None,
    ):
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self.max_retries = max_retries
        self.sleep = sleep
        self.client_factory = client_factory or (lambda api_key: genai.Client(api_key=api_key))
        self.clients = []
        self.next_client_index = 0

        if client is not None:
            self.clients = [client]
        else:
            self.clients = [self.client_factory(api_key) for api_key in (api_keys or _env_api_keys())]

    def _ordered_clients(self):
        total = len(self.clients)
        start = self.next_client_index % total
        return [self.clients[(start + offset) % total] for offset in range(total)]

    def _advance_client(self):
        self.next_client_index = (self.next_client_index + 1) % len(self.clients)

    def generate_json(self, prompt, response_schema, temperature=0.1):
        last_error = None
        for client in self._ordered_clients():
            for attempt in range(self.max_retries):
                try:
                    response = client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config={
                            "temperature": temperature,
                            "response_mime_type": "application/json",
                            "response_json_schema": response_schema,
                        },
                    )
                    self._advance_client()
                    return json.loads(response.text)
                except (
                    ValueError,
                    TypeError,
                    json.JSONDecodeError,
                    RuntimeError,
                    errors.APIError,
                ) as exc:
                    last_error = exc
                    if isinstance(exc, errors.APIError):
                        if _api_error_status(exc) == 429:
                            break
                        if not _is_retryable_api_error(exc):
                            raise RuntimeError(
                                f"Gemini JSON generation failed: {last_error}"
                            ) from last_error
                    if attempt + 1 < self.max_retries:
                        self.sleep(2**attempt)

        raise RuntimeError(f"Gemini JSON generation failed: {last_error}") from last_error


def get_default_client():
    global _default_client
    if _default_client is None:
        _default_client = GeminiJsonClient()
    return _default_client


def close_default_client():
    global _default_client
    if _default_client is not None:
        for client in getattr(_default_client, "clients", []):
            close = getattr(client, "close", None)
            if close is not None:
                close()
        _default_client = None


def generate_json(prompt, response_schema, temperature=0.1):
    return get_default_client().generate_json(prompt, response_schema, temperature)
