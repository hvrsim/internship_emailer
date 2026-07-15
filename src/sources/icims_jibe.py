"""iCIMS career sites using the Jibe public search API."""

from __future__ import annotations

import requests

from ..models import Job
from .base import Source, request_json

PAGE = 100


class JibeSource(Source):
    def __init__(
        self,
        company: str,
        base_url: str,
        job_path_prefix: str,
        search_text: str = "intern",
    ):
        self.company = company
        self.base_url = base_url.rstrip("/")
        self.job_path_prefix = "/" + job_path_prefix.strip("/") + "/"
        self.search_text = search_text
        self.name = f"icims-jibe:{company}"

    def fetch(self, session: requests.Session) -> list[Job]:
        jobs: list[Job] = []
        page = 1
        while True:
            data = request_json(
                session,
                "GET",
                f"{self.base_url}/api/jobs",
                params={
                    "keywords": self.search_text,
                    "page": page,
                    "pagesize": PAGE,
                },
            )
            if not data or not isinstance(data, dict):
                break
            postings = data.get("jobs") or []
            for wrapped in postings:
                raw = wrapped.get("data") or {}
                title = raw.get("title")
                slug = raw.get("slug")
                if not (title and slug):
                    continue
                location = raw.get("full_location") or raw.get("short_location")
                jobs.append(
                    Job(
                        company=self.company,
                        title=str(title),
                        url=f"{self.base_url}{self.job_path_prefix}{slug}",
                        locations=[str(location)] if location else [],
                        source=self.name,
                        ats="icims",
                        posted_date=(raw.get("posted_date") or "")[:10] or None,
                    )
                )
            if not postings or page * PAGE >= int(data.get("totalCount", 0)):
                break
            page += 1
        return jobs
