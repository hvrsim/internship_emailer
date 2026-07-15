"""Build the full list of Source objects from config."""

from __future__ import annotations

import logging

from .. import config
from . import github_lists
from .amazon import AmazonSource
from .ashby import AshbySource
from .base import Source
from .epic import EpicSource
from .greenhouse import GreenhouseSource
from .icims_jibe import JibeSource
from .lever import LeverSource
from .oracle_cloud import OracleCloudSource
from .shopify import ShopifySource
from .smartrecruiters import SmartRecruitersSource
from .tiktok import TikTokSource
from .workday import WorkdaySource

log = logging.getLogger(__name__)


def _enabled(entry: dict) -> bool:
    return entry.get("enabled", True) is not False


def build_all_sources() -> list[Source]:
    sources: list[Source] = []

    # 1) Community internship aggregators.
    sources.extend(github_lists.build_sources())

    # 2) Company ATS APIs.
    comp = config.companies()

    for e in comp.get("greenhouse", []) or []:
        if _enabled(e) and e.get("token"):
            sources.append(GreenhouseSource(e["company"], e["token"]))

    for e in comp.get("lever", []) or []:
        if _enabled(e) and e.get("token"):
            sources.append(LeverSource(e["company"], e["token"]))

    for e in comp.get("ashby", []) or []:
        if _enabled(e) and e.get("token"):
            sources.append(AshbySource(e["company"], e["token"]))

    for e in comp.get("workday", []) or []:
        if _enabled(e) and e.get("tenant") and e.get("site"):
            sources.append(
                WorkdaySource(
                    e["company"], e["tenant"], e.get("wd_num", 1), e["site"]
                )
            )

    for e in comp.get("smartrecruiters", []) or []:
        if _enabled(e) and e.get("token"):
            sources.append(SmartRecruitersSource(e["company"], e["token"]))

    for e in comp.get("amazon", []) or []:
        if _enabled(e):
            sources.append(
                AmazonSource(
                    e["company"],
                    e.get("search_text", "intern"),
                    e.get("title_company_term"),
                    e.get("exclude_title_terms"),
                )
            )

    for e in comp.get("oracle_cloud", []) or []:
        if (
            _enabled(e)
            and e.get("host")
            and e.get("site_number")
            and e.get("job_url_template")
        ):
            sources.append(
                OracleCloudSource(
                    e["company"],
                    e["host"],
                    e["site_number"],
                    e["job_url_template"],
                    e.get("search_text", "intern"),
                )
            )

    for e in comp.get("icims_jibe", []) or []:
        if _enabled(e) and e.get("base_url") and e.get("job_path_prefix"):
            sources.append(
                JibeSource(
                    e["company"],
                    e["base_url"],
                    e["job_path_prefix"],
                    e.get("search_text", "intern"),
                )
            )

    for e in comp.get("custom", []) or []:
        if _enabled(e) and e.get("provider") == "epic":
            sources.append(EpicSource())
        elif _enabled(e) and e.get("provider") == "shopify":
            sources.append(ShopifySource())
        elif _enabled(e) and e.get("provider") == "tiktok":
            sources.append(TikTokSource())

    log.info("built %d sources", len(sources))
    return sources
