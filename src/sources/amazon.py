"""Amazon's public careers search endpoint."""

from __future__ import annotations

from datetime import datetime

import requests

from ..models import Job
from .base import Source, request_json

API = "https://www.amazon.jobs/en/search.json"
PAGE = 100


class AmazonSource(Source):
    def __init__(
        self,
        company: str,
        search_text: str = "intern",
        title_company_term: str | None = None,
        exclude_title_terms: list[str] | None = None,
    ):
        self.company = company
        self.search_text = search_text
        self.title_company_term = title_company_term
        self.exclude_title_terms = [term.lower() for term in exclude_title_terms or []]
        self.name = f"amazon:{company}"

    def fetch(self, session: requests.Session) -> list[Job]:
        jobs: list[Job] = []
        offset = 0
        while True:
            data = request_json(
                session,
                "GET",
                API,
                params={
                    "base_query": self.search_text,
                    "offset": offset,
                    "result_limit": PAGE,
                },
            )
            if not data or not isinstance(data, dict):
                break
            postings = data.get("jobs") or []
            for raw in postings:
                title = str(raw.get("title", ""))
                if (
                    self.title_company_term
                    and self.title_company_term.lower() not in title.lower()
                ):
                    continue
                if any(term in title.lower() for term in self.exclude_title_terms):
                    continue
                country_code = str(raw.get("country_code", "")).upper()
                if country_code and country_code != "USA":
                    continue
                path = raw.get("job_path")
                if not (title and path):
                    continue
                location = raw.get("normalized_location") or raw.get("location")
                posted_date = None
                if raw.get("posted_date"):
                    try:
                        posted_date = datetime.strptime(
                            raw["posted_date"], "%B %d, %Y"
                        ).date().isoformat()
                    except (TypeError, ValueError):
                        posted_date = None
                jobs.append(
                    Job(
                        company=self.company,
                        title=str(title),
                        url=f"https://www.amazon.jobs{path}",
                        locations=[str(location)] if location else [],
                        source=self.name,
                        ats="amazon",
                        posted_date=posted_date,
                    )
                )
            offset += len(postings)
            if not postings or offset >= int(data.get("hits", 0)):
                break
        return jobs
