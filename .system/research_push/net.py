from __future__ import annotations

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


USER_AGENT = "research_push/0.1 (+https://github.com/huangwenjie2023/research_push)"


def fetch_bytes(url: str, headers: dict[str, str] | None = None, timeout: int = 30, retries: int = 2) -> bytes:
    request_headers = {"User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    request = Request(url, headers=request_headers)
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.read()
        except HTTPError as error:
            if error.code != 429 or attempt >= retries:
                raise
            retry_after = error.headers.get("Retry-After")
            delay = int(retry_after) if retry_after and retry_after.isdigit() else 5 * (attempt + 1)
            time.sleep(delay)
    raise RuntimeError("unreachable fetch retry state")


def fetch_json(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> dict:
    return json.loads(fetch_bytes(url, headers=headers, timeout=timeout).decode("utf-8"))


def post_json(url: str, payload: dict, headers: dict[str, str] | None = None, timeout: int = 60) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    request_headers.update(headers or {})
    request = Request(url, data=body, headers=request_headers, method="POST")
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def env_header(env_name: str | None, template: str = "Bearer {value}") -> dict[str, str]:
    if not env_name:
        return {}
    value = os.environ.get(env_name)
    if not value:
        return {}
    return {"Authorization": template.format(value=value)}


def network_error_message(error: Exception) -> str:
    if isinstance(error, HTTPError):
        return f"HTTP {error.code}: {error.reason}"
    if isinstance(error, URLError):
        return str(error.reason)
    return str(error)
