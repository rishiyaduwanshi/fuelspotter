from __future__ import annotations

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

try:
    from dotenv import load_dotenv
except ImportError as exc:  # pragma: no cover
    raise ImproperlyConfigured(
        "python-dotenv is required. Install it with: pip install python-dotenv"
    ) from exc


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(dotenv_path=BASE_DIR / ".env", override=True)


def env_str(name: str, default: str | None = None, *, required: bool = False) -> str | None:
    value = os.getenv(name, default)
    if required and (value is None or value.strip() == ""):
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")
    if value is None:
        return None
    value = value.strip()
    return value if value != "" else None


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.strip().lower()
    if raw in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ImproperlyConfigured(
        f"Invalid boolean for {name}: {raw!r} (use true/false)"
    )


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return default or []
    raw = raw.strip()
    if raw == "":
        return []
    # Accept comma-separated values.
    return [item.strip() for item in raw.split(",") if item.strip()]


# Public config used by Django settings
DEBUG = env_bool("DEBUG", default=False)

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", default=[])

_default_dev_secret = "django-insecure-c6-h3+9nm9z#!nmm$r5qo8j483*cbpspw1_n28n#)r7*=h^wbg"
SECRET_KEY = env_str("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = _default_dev_secret
    else:
        raise ImproperlyConfigured("SECRET_KEY must be set in production")
