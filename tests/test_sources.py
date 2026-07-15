"""Configured source coverage."""

from unittest.mock import Mock, patch

from src import config
from src.sources.amazon import AmazonSource
from src.sources.epic import EpicSource
from src.sources.icims_jibe import JibeSource
from src.sources.oracle_cloud import OracleCloudSource
from src.sources.shopify import ShopifySource
from src.sources.smartrecruiters import SmartRecruitersSource
from src.sources.tiktok import TikTokSource


def test_additional_company_sources_are_configured_once():
    companies = config.companies()
    providers = (
        "greenhouse",
        "lever",
        "ashby",
        "workday",
        "smartrecruiters",
        "amazon",
        "oracle_cloud",
        "icims_jibe",
        "custom",
    )
    names = [
        entry["company"]
        for ats in providers
        for entry in companies.get(ats, [])
        if entry.get("enabled", True)
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
        "Amazon",
        "Epic",
        "GitHub",
        "LinkedIn",
        "Oracle",
        "Shopify",
        "SIG Trading",
        "TikTok",
        "Uber",
    }
    assert expected <= set(names)
    assert len(names) == len(set(names))


def test_smartrecruiters_maps_postings():
    data = {
        "totalFound": 1,
        "content": [
            {
                "id": "123",
                "name": "Software Engineering Intern",
                "releasedDate": "2026-07-01T12:00:00Z",
                "location": {"fullLocation": "Sunnyvale, CA, United States"},
            }
        ],
    }
    with patch("src.sources.smartrecruiters.request_json", return_value=data):
        jobs = SmartRecruitersSource("LinkedIn", "LinkedIn3").fetch(Mock())

    assert jobs[0].url == "https://jobs.smartrecruiters.com/LinkedIn3/123"
    assert jobs[0].locations == ["Sunnyvale, CA, United States"]


def test_amazon_maps_search_results():
    data = {
        "hits": 1,
        "jobs": [
            {
                "title": "Software Development Engineer Intern",
                "job_path": "/en/jobs/123/software-intern",
                "location": "US, CA, Seattle",
                "normalized_location": "Seattle, Washington, USA",
                "country_code": "USA",
                "posted_date": "July 1, 2026",
            }
        ],
    }
    with patch("src.sources.amazon.request_json", return_value=data):
        jobs = AmazonSource("Amazon").fetch(Mock())

    assert jobs[0].url == "https://www.amazon.jobs/en/jobs/123/software-intern"
    assert jobs[0].locations == ["Seattle, Washington, USA"]
    assert jobs[0].posted_date == "2026-07-01"


def test_amazon_skips_non_us_and_excluded_subsidiary_roles():
    data = {
        "hits": 2,
        "jobs": [
            {
                "title": "Software Engineering Intern",
                "job_path": "/en/jobs/1/intern",
                "country_code": "CAN",
            },
            {
                "title": "Software Engineering Intern, Annapurna Labs",
                "job_path": "/en/jobs/2/annapurna-intern",
                "country_code": "USA",
            },
        ],
    }
    with patch("src.sources.amazon.request_json", return_value=data):
        jobs = AmazonSource("Amazon", exclude_title_terms=["Annapurna"]).fetch(Mock())

    assert jobs == []


def test_oracle_cloud_maps_primary_and_secondary_locations():
    data = {
        "items": [
            {
                "TotalJobsCount": 1,
                "requisitionList": [
                    {
                        "Id": "42",
                        "Title": "Software Engineering Intern",
                        "PostedDate": "2026-07-01",
                        "PrimaryLocation": "New York, NY, United States",
                        "secondaryLocations": [{"Name": "San Francisco, CA, United States"}],
                    }
                ],
            }
        ]
    }
    with patch("src.sources.oracle_cloud.request_json", return_value=data):
        jobs = OracleCloudSource(
            "Uber",
            "https://example.oraclecloud.com",
            "CX_1",
            "https://jobs.example.com/{id}/",
        ).fetch(Mock())

    assert jobs[0].url == "https://jobs.example.com/42/"
    assert jobs[0].locations == [
        "New York, NY, United States",
        "San Francisco, CA, United States",
    ]


def test_jibe_maps_wrapped_job_data():
    data = {
        "totalCount": 1,
        "jobs": [
            {
                "data": {
                    "slug": "99",
                    "title": "Software Engineering Intern",
                    "full_location": "New York, New York",
                    "posted_date": "2026-07-01T00:00:00+0000",
                }
            }
        ],
    }
    with patch("src.sources.icims_jibe.request_json", return_value=data):
        jobs = JibeSource("SIG", "https://careers.example.com", "jobs").fetch(Mock())

    assert jobs[0].url == "https://careers.example.com/jobs/99"
    assert jobs[0].posted_date == "2026-07-01"


def test_custom_html_sources_parse_published_jobs():
    epic_page = (
        '<script>self.__next_f.push([1,"x:{\\"allOpenJobs\\":[{\\"id\\":\\"7\\"}],'
        '\\"avaturePositions\\":{\\"7\\":{\\"externalName\\":\\"Software Developer '
        'Intern\\"}}}"])</script>'
    )
    shopify_page = """
    <a href="/careers/software-intern_abc">
      <h4>Software Engineering Intern</h4>
      <div class="location"><span>Remote - Americas</span></div>
    </a>
    """
    with patch("src.sources.epic.request_text", return_value=epic_page):
        epic_jobs = EpicSource().fetch(Mock())
    with patch("src.sources.shopify.request_text", return_value=shopify_page):
        shopify_jobs = ShopifySource().fetch(Mock())

    assert epic_jobs[0].title == "Software Developer Intern"
    assert shopify_jobs[0].locations == ["Remote - Americas"]


def test_tiktok_maps_nested_location():
    data = {
        "data": {
            "count": 1,
            "job_post_list": [
                {
                    "id": "123",
                    "title": "Software Engineering Intern",
                    "city_info": {
                        "en_name": "San Jose",
                        "parent": {
                            "en_name": "California",
                            "parent": {"en_name": "United States", "parent": None},
                        },
                    },
                }
            ],
        }
    }
    with patch("src.sources.tiktok.request_json", return_value=data):
        jobs = TikTokSource().fetch(Mock())

    assert jobs[0].url == "https://lifeattiktok.com/search/123"
    assert jobs[0].locations == ["San Jose, California, United States"]
