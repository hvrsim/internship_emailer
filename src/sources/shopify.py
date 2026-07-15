"""Shopify's server-rendered public careers page."""

from __future__ import annotations

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ..models import Job
from .base import Source, request_text

CAREERS_URL = "https://www.shopify.com/careers"


class ShopifySource(Source):
    name = "shopify:Shopify"

    def fetch(self, session: requests.Session) -> list[Job]:
        page = request_text(session, CAREERS_URL)
        if not page:
            return []
        soup = BeautifulSoup(page, "html.parser")
        jobs: list[Job] = []
        for link in soup.select('a[href^="/careers/"]'):
            href = str(link.get("href", ""))
            if "_" not in href:
                continue
            title_node = link.find("h4")
            location_node = link.select_one(".location span")
            if not title_node:
                continue
            title = title_node.get_text(" ", strip=True)
            location = (
                location_node.get_text(" ", strip=True) if location_node else ""
            )
            jobs.append(
                Job(
                    company="Shopify",
                    title=title,
                    url=urljoin(CAREERS_URL, href),
                    locations=[location] if location else [],
                    source=self.name,
                    ats="custom",
                )
            )
        return jobs
