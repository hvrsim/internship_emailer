"""Configured source coverage."""

from src import config


def test_additional_company_sources_are_configured_once():
    companies = config.companies()
    names = [
        entry["company"]
        for ats in ("greenhouse", "lever", "ashby", "workday")
        for entry in companies.get(ats, [])
    ]

    expected = {
        "Five Rings",
        "Datadog",
        "Waymo",
        "Glean",
        "Cohere",
        "Snowflake",
        "Lyft",
        "Belvedere Trading",
        "Visa",
    }
    assert expected <= set(names)
    assert len(names) == len(set(names))
