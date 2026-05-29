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


class GeminiJsonClient:
    def __init__(self, client=None, model=None, max_retries=3, sleep=time.sleep):
        self.client = client or genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        self.model = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
        self.max_retries = max_retries
        self.sleep = sleep

    def generate_json(self, prompt, response_schema, temperature=0.1):
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": temperature,
                        "response_mime_type": "application/json",
                        "response_json_schema": response_schema,
                    },
                )
                return json.loads(response.text)
            except (
                ValueError,
                TypeError,
                json.JSONDecodeError,
                RuntimeError,
                errors.APIError,
            ) as exc:
                last_error = exc
                if isinstance(exc, errors.APIError) and not _is_retryable_api_error(exc):
                    break
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
        close = getattr(getattr(_default_client, "client", None), "close", None)
        if close is not None:
            close()
        _default_client = None


def generate_json(prompt, response_schema, temperature=0.1):
    return get_default_client().generate_json(prompt, response_schema, temperature)
