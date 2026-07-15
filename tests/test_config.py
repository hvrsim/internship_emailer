"""Configuration loading behavior."""

from src.config import _apply_environment_overrides, _deep_merge


def test_deep_merge_preserves_defaults_and_applies_local_overrides():
    base = {
        "discord": {"enabled": True, "webhook_url": "", "timeout_seconds": 20},
        "prune_after_days": 120,
    }
    local = {"discord": {"webhook_url": "https://discord.example/webhook"}}

    assert _deep_merge(base, local) == {
        "discord": {
            "enabled": True,
            "webhook_url": "https://discord.example/webhook",
            "timeout_seconds": 20,
        },
        "prune_after_days": 120,
    }


def test_environment_webhook_overrides_yaml(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/from-env")

    values = _apply_environment_overrides(
        {"discord": {"enabled": True, "webhook_url": "https://discord.example/from-yaml"}}
    )

    assert values["discord"]["enabled"] is True
    assert values["discord"]["webhook_url"] == "https://discord.example/from-env"
