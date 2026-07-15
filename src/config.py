"""Configuration + secrets loading."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Repo root = parent of the `src/` package.
ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"

# Load .env once on import (no-op if the file is absent, e.g. in CI where
# secrets come from the environment directly).
load_dotenv(ROOT / ".env")


def _load_yaml(name: str) -> dict[str, Any]:
    path = CONFIG_DIR / name
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_environment_overrides(values: dict[str, Any]) -> dict[str, Any]:
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return values
    return _deep_merge(values, {"discord": {"webhook_url": webhook_url}})


@lru_cache(maxsize=None)
def filters() -> dict[str, Any]:
    return _load_yaml("filters.yaml")


@lru_cache(maxsize=None)
def github_lists() -> dict[str, Any]:
    return _load_yaml("github_lists.yaml")


@lru_cache(maxsize=None)
def companies() -> dict[str, Any]:
    return _load_yaml("companies.yaml")


@lru_cache(maxsize=None)
def settings() -> dict[str, Any]:
    return _apply_environment_overrides(
        _deep_merge(
            _load_yaml("settings.yaml"),
            _load_yaml("settings.local.yaml"),
        )
    )


def state_path() -> Path:
    rel = settings().get("state_file", "data/seen_jobs.json")
    return ROOT / rel
