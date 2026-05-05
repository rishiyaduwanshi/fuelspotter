from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class HttpJsonResponse:
    status_code: int
    json: Any


class HttpError(RuntimeError):
    pass


def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout_s: float = 10.0,
) -> HttpJsonResponse:
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout_s)
    except requests.RequestException as exc:
        raise HttpError(str(exc)) from exc

    content_type = (resp.headers.get('content-type') or '').lower()
    if resp.status_code >= 400:
        raise HttpError(f"HTTP {resp.status_code} from {url}")
    if 'application/json' not in content_type and 'application/geo+json' not in content_type:
        # Still try JSON decode because some APIs send incorrect headers.
        pass

    try:
        data = resp.json()
    except ValueError as exc:
        raise HttpError(f"Invalid JSON from {url}") from exc

    return HttpJsonResponse(status_code=resp.status_code, json=data)
