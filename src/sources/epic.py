"""Epic's careers page, which embeds its published Avature positions."""

from __future__ import annotations

import json

import requests

from ..models import Job
from .base import Source, request_text

CAREERS_URL = "https://careers.epic.com/jobs/"
_POSITIONS_MARKER = '"allOpenJobs":'
_DETAILS_MARKER = '"avaturePositions":'


def _next_data_chunk(page: str) -> str:
    marker_index = page.find("avaturePositions")
    if marker_index < 0:
        return ""
    start = page.rfind("self.__next_f.push([1,", 0, marker_index)
    if start < 0:
        return ""
    value_start = page.find(",", start) + 1
    try:
        value, _ = json.JSONDecoder().raw_decode(page[value_start:])
    except json.JSONDecodeError:
        return ""
    return value if isinstance(value, str) else ""


def _embedded_value(chunk: str, marker: str):
    start = chunk.find(marker)
    if start < 0:
        return None
    starts = [
        index
        for index in (chunk.find("{", start), chunk.find("[", start))
        if index >= 0
    ]
    start = min(starts) if starts else -1
    if start < 0:
        return None
    try:
        value, _ = json.JSONDecoder().raw_decode(chunk[start:])
    except json.JSONDecodeError:
        return None
    return value


class EpicSource(Source):
    name = "epic:Epic"

    def fetch(self, session: requests.Session) -> list[Job]:
        page = request_text(session, CAREERS_URL)
        if not page:
            return []
        chunk = _next_data_chunk(page)
        open_jobs = _embedded_value(chunk, _POSITIONS_MARKER) or []
        positions = _embedded_value(chunk, _DETAILS_MARKER) or {}
        jobs: list[Job] = []
        for entry in open_jobs:
            posting_id = str(entry.get("id", ""))
            raw = positions.get(posting_id) or {}
            title = raw.get("externalName")
            if not (posting_id and title):
                continue
            jobs.append(
                Job(
                    company="Epic",
                    title=str(title),
                    url=f"https://careers.epic.com/jobs/{posting_id}/",
                    locations=["Verona, WI"],
                    source=self.name,
                    ats="avature",
                )
            )
        return jobs
