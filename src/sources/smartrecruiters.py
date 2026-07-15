"""SmartRecruiters public postings API."""

from __future__ import annotations

import requests

from ..models import Job
from .base import Source, request_json

API = "https://api.smartrecruiters.com/v1/companies/{token}/postings"
PAGE = 100


class SmartRecruitersSource(Source):
    def __init__(self, company: str, token: str):
        self.company = company
        self.token = token
        self.name = f"smartrecruiters:{company}"

    def fetch(self, session: requests.Session) -> list[Job]:
        jobs: list[Job] = []
        offset = 0
        while True:
            data = request_json(
                session,
                "GET",
                API.format(token=self.token),
                params={"limit": PAGE, "offset": offset},
            )
            if not data or not isinstance(data, dict):
                break
            postings = data.get("content") or []
            for raw in postings:
                title = raw.get("name")
                posting_id = raw.get("id")
                if not (title and posting_id):
                    continue
                location = raw.get("location") or {}
                full_location = location.get("fullLocation")
                jobs.append(
                    Job(
                        company=self.company,
                        title=str(title),
                        url=f"https://jobs.smartrecruiters.com/{self.token}/{posting_id}",
                        locations=[str(full_location)] if full_location else [],
                        source=self.name,
                        ats="smartrecruiters",
                        posted_date=(raw.get("releasedDate") or "")[:10] or None,
                    )
                )
            offset += len(postings)
            if not postings or offset >= int(data.get("totalFound", 0)):
                break
        return jobs
