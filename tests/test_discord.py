"""Discord webhook notification behavior."""

from unittest.mock import Mock, patch

from src.models import Job
from src.notify import discord

PRIORITY = ["meta", "amazon", "apple", "netflix", "google"]


def _job(company: str, category: str = "swe") -> Job:
    return Job(
        company=company,
        title="Software Engineer Intern",
        url=f"https://example.com/{company}",
        locations=["New York, NY"],
        category=category,
        season="summer",
        year=2027,
    )


def test_priority_company_uses_token_matching():
    assert discord.is_priority_company("Apple Inc", PRIORITY)
    assert not discord.is_priority_company("Snapple", PRIORITY)


def test_payload_groups_jobs_without_text_above_the_cards():
    payloads = discord.build_payloads(
        [_job("Meta"), _job("Acme", "other")],
        {
            "category_order": ["swe", "other"],
            "priority_companies": PRIORITY,
            "username": "Intern Alerts",
        },
    )

    assert "content" not in payloads[0]
    assert payloads[0]["username"] == "Intern Alerts"
    assert payloads[0]["avatar_url"] == discord._DEFAULT_AVATAR_URL
    assert [embed["title"] for embed in payloads[0]["embeds"]] == [
        "💻 Software Engineering · 1 role",
        "🧩 Other Opportunities · 1 role",
    ]
    assert payloads[0]["allowed_mentions"] == {"parse": []}


def test_payload_formats_each_job_as_a_clean_linked_card():
    job = _job("Acme")
    job.title = "Software Engineer Intern (Summer 2027)"
    payload = discord.build_payloads([job], {})[0]
    embed = payload["embeds"][0]

    assert embed["description"] == (
        "**[Software Engineer Intern (Summer 2027)](https://example.com/Acme)**\n"
        "Acme — New York, NY\n"
        "Summer 2027 Internship"
    )
    assert "footer" not in embed
    assert embed["color"] == 0x5865F2


def test_send_discord_posts_to_webhook_from_settings():
    response = Mock()
    response.raise_for_status.return_value = None
    config = {"webhook_url": "https://discord.com/api/webhooks/example", "timeout_seconds": 7}

    with patch("src.notify.discord.requests.post", return_value=response) as post:
        assert discord.send_discord([_job("Acme")], config)

    post.assert_called_once()
    assert post.call_args.args[0] == config["webhook_url"]
    assert post.call_args.kwargs["timeout"] == 7


def test_send_discord_skips_when_webhook_is_missing():
    with patch("src.notify.discord.requests.post") as post:
        assert not discord.send_discord([_job("Acme")], {})
    post.assert_not_called()


def test_send_discord_retries_rate_limit():
    rate_limited = Mock(status_code=429)
    rate_limited.json.return_value = {"retry_after": 0.25}
    sent = Mock(status_code=204)
    sent.raise_for_status.return_value = None

    with (
        patch("src.notify.discord.requests.post", side_effect=[rate_limited, sent]) as post,
        patch("src.notify.discord.time.sleep") as sleep,
    ):
        assert discord.send_discord(
            [_job("Acme")],
            {
                "webhook_url": "https://discord.com/api/webhooks/example",
                "max_retries": 1,
            },
        )

    assert post.call_count == 2
    sleep.assert_called_once_with(0.25)
