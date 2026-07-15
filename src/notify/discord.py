"""Discord webhook notifications."""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import quote

import requests

from ..models import Job

log = logging.getLogger(__name__)

_CATEGORY_LABELS = {
    "swe": "💻 Software Engineering",
    "other": "🧩 Other Opportunities",
}
_CATEGORY_COLORS = {
    "swe": 0x5865F2,
    "other": 0x99AAB5,
}
_DEFAULT_AVATAR_URL = (
    "https://cdn.jsdelivr.net/npm/twemoji@14.0.2/assets/72x72/1f514.png"
)
_MAX_EMBED_DESCRIPTION = 3_800
_MAX_EMBED_TEXT_PER_MESSAGE = 5_800


def is_priority_company(company: str, terms: list[str]) -> bool:
    """Token-based match so 'apple' hits 'Apple Inc' but not 'Snapple'."""
    tokens = set(re.findall(r"[a-z0-9]+", (company or "").lower()))
    return any(term.lower() in tokens for term in terms or [])


def priority_jobs(jobs: list[Job], terms: list[str]) -> list[Job]:
    return [job for job in jobs if is_priority_company(job.company, terms)]


def group_by_category(jobs: list[Job], order: list[str]) -> list[tuple[str, list[Job]]]:
    buckets: dict[str, list[Job]] = {}
    for job in jobs:
        buckets.setdefault(job.category or "other", []).append(job)
    ordered_keys = [category for category in order if category in buckets]
    ordered_keys += [category for category in buckets if category not in order]
    return [(category, buckets[category]) for category in ordered_keys]


def _escape_markdown(value: str) -> str:
    return re.sub(r"([\\*_`~|>\[\]#])", r"\\\1", value)


def _job_card(job: Job) -> str:
    title = _escape_markdown(job.title[:256])
    company = _escape_markdown(job.company[:128])
    location = _escape_markdown(job.location_str[:256] or "Location not listed")
    season = job.season.title() if job.season else None
    term = " ".join(value for value in (season, str(job.year) if job.year else None) if value)
    url = quote(job.url[:1_800], safe=":/?#@!$&'*+,;=%")

    internship_term = f"{_escape_markdown(term)} Internship" if term else "Internship"
    return f"**[{title}]({url})**\n{company} — {location}\n{internship_term}"


def _role_count(count: int) -> str:
    return f"{count} {'role' if count == 1 else 'roles'}"


def _category_embeds(category: str, jobs: list[Job]) -> list[dict]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for job in sorted(jobs, key=lambda item: (item.company.lower(), item.title.lower())):
        card = _job_card(job)
        added_length = len(card) + (2 if current else 0)
        if current and current_length + added_length > _MAX_EMBED_DESCRIPTION:
            chunks.append("\n\n".join(current))
            current = []
            current_length = 0
        current.append(card)
        current_length += len(card) + (2 if len(current) > 1 else 0)
    if current:
        chunks.append("\n\n".join(current))

    label = _CATEGORY_LABELS.get(category, category.title())
    return [
        {
            "title": f"{label} · {_role_count(len(jobs))}"
            + (f" · Part {index + 1}/{len(chunks)}" if len(chunks) > 1 else ""),
            "description": chunk,
            "color": _CATEGORY_COLORS.get(category, _CATEGORY_COLORS["other"]),
        }
        for index, chunk in enumerate(chunks)
    ]


def build_payloads(jobs: list[Job], discord_cfg: dict) -> list[dict]:
    order = discord_cfg.get("category_order", ["swe", "other"])
    grouped = group_by_category(jobs, order)

    embeds = [
        embed
        for category, category_jobs in grouped
        for embed in _category_embeds(category, category_jobs)
    ]
    payloads: list[dict] = []
    current: list[dict] = []
    current_length = 0
    for embed in embeds:
        embed_length = len(embed["title"]) + len(embed["description"])
        if current and (
            len(current) >= 10
            or current_length + embed_length > _MAX_EMBED_TEXT_PER_MESSAGE
        ):
            payloads.append({"embeds": current})
            current = []
            current_length = 0
        current.append(embed)
        current_length += embed_length
    if current:
        payloads.append({"embeds": current})
    if not payloads:
        payloads.append({})

    for payload in payloads:
        payload["username"] = discord_cfg.get("username", "Intern Alerts")
        avatar_url = discord_cfg.get("avatar_url", _DEFAULT_AVATAR_URL)
        if avatar_url:
            payload["avatar_url"] = avatar_url
        payload["allowed_mentions"] = {"parse": []}
    return payloads


def send_discord(jobs: list[Job], discord_cfg: dict) -> bool:
    """Send the digest to the configured Discord webhook."""
    webhook_url = str(discord_cfg.get("webhook_url", "")).strip()
    if not webhook_url:
        log.warning("discord skipped: discord.webhook_url is not set in config/settings.yaml")
        return False

    timeout = discord_cfg.get("timeout_seconds", 20)
    max_retries = discord_cfg.get("max_retries", 3)
    inter_message_delay = discord_cfg.get("inter_message_delay_seconds", 0.5)
    try:
        payloads = build_payloads(jobs, discord_cfg)
        for index, payload in enumerate(payloads):
            for attempt in range(max_retries + 1):
                response = requests.post(webhook_url, json=payload, timeout=timeout)
                if response.status_code != 429:
                    response.raise_for_status()
                    break
                if attempt == max_retries:
                    response.raise_for_status()
                try:
                    retry_after = float(response.json().get("retry_after", 1))
                except (TypeError, ValueError, requests.JSONDecodeError):
                    retry_after = 1
                time.sleep(max(retry_after, 0))
            if index < len(payloads) - 1:
                time.sleep(inter_message_delay)
        log.info("discord alert sent (%d jobs in %d message(s))", len(jobs), len(payloads))
        return True
    except requests.RequestException as exc:
        log.error("discord send failed: %s", exc)
        return False
