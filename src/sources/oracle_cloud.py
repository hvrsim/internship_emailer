"""Oracle Recruiting Cloud candidate-experience API."""

from __future__ import annotations

import requests

from ..models import Job
from .base import Source, request_json

PAGE = 100


class OracleCloudSource(Source):
    def __init__(
        self,
        company: str,
        host: str,
        site_number: str,
        job_url_template: str,
        search_text: str = "intern",
    ):
        self.company = company
        self.host = host.rstrip("/")
        self.site_number = site_number
        self.job_url_template = job_url_template
        self.search_text = search_text
        self.name = f"oracle-cloud:{company}"
        self.api = (
            f"{self.host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        )

    def fetch(self, session: requests.Session) -> list[Job]:
        jobs: list[Job] = []
        offset = 0
        while True:
            finder = (
                f"findReqs;siteNumber={self.site_number},"
                f"limit={PAGE},offset={offset},keyword={self.search_text}"
            )
            data = request_json(
                session,
                "GET",
                self.api,
                params={
                    "onlyData": "true",
                    "expand": "requisitionList.secondaryLocations",
                    "finder": finder,
                },
            )
            if not data or not isinstance(data, dict):
                break
            results = data.get("items") or []
            if not results:
                break
            result = results[0]
            postings = result.get("requisitionList") or []
            for raw in postings:
                title = raw.get("Title")
                posting_id = raw.get("Id")
                if not (title and posting_id):
                    continue
                locations = []
                if raw.get("PrimaryLocation"):
                    locations.append(str(raw["PrimaryLocation"]))
                for secondary in raw.get("secondaryLocations", []) or []:
                    location = secondary.get("Name")
                    if location and location not in locations:
                        locations.append(str(location))
                jobs.append(
                    Job(
                        company=self.company,
                        title=str(title),
                        url=self.job_url_template.format(id=posting_id),
                        locations=locations,
                        source=self.name,
                        ats="oracle-cloud",
                        posted_date=raw.get("PostedDate"),
                    )
                )
            offset += len(postings)
            if not postings or offset >= int(result.get("TotalJobsCount", 0)):
                break
        return jobs
