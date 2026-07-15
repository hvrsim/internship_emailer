"""TikTok's public Life at TikTok job-search API."""

from __future__ import annotations

import requests

from ..models import Job
from .base import Source, request_json

API = "https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts"
PAGE = 100
HEADERS = {
    "accept-language": "en-US",
    "origin": "https://lifeattiktok.com",
    "website-path": "tiktok",
}


def _location(raw: dict) -> str:
    names: list[str] = []
    current = raw.get("city_info")
    while isinstance(current, dict):
        name = current.get("en_name") or current.get("i18n_name")
        if name and name not in names:
            names.append(str(name))
        current = current.get("parent")
    return ", ".join(names)


class TikTokSource(Source):
    name = "tiktok:TikTok"

    def fetch(self, session: requests.Session) -> list[Job]:
        jobs: list[Job] = []
        page = 1
        while True:
            data = request_json(
                session,
                "POST",
                API,
                json_body={"keyword": "intern", "page_size": PAGE, "page": page},
                headers=HEADERS,
            )
            if not data or not isinstance(data, dict):
                break
            result = data.get("data") or {}
            postings = result.get("job_post_list") or []
            for raw in postings:
                title = raw.get("title")
                posting_id = raw.get("id")
                if not (title and posting_id):
                    continue
                location = _location(raw)
                jobs.append(
                    Job(
                        company="TikTok",
                        title=str(title),
                        url=f"https://lifeattiktok.com/search/{posting_id}",
                        locations=[location] if location else [],
                        source=self.name,
                        ats="byteapply",
                    )
                )
            if not postings or page * PAGE >= int(result.get("count", 0)):
                break
            page += 1
        return jobs
