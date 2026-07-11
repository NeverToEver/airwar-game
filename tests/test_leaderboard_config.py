"""Tests for leaderboard runtime configuration validation."""

from __future__ import annotations

import pytest

from airwar.leaderboard.config import LeaderboardConfig, _DEFAULT_TIMEOUT, _DEFAULT_URL


class TestLeaderboardConfigDefaults:
    def test_default_values(self, monkeypatch):
        for key in (
            "AIRWAR_LEADERBOARD_URL",
            "AIRWAR_LEADERBOARD_TIMEOUT",
            "AIRWAR_LEADERBOARD_MODE",
            "AIRWAR_LEADERBOARD_DB_PATH",
            "AIRWAR_LEADERBOARD_CORS_ORIGINS",
        ):
            monkeypatch.delenv(key, raising=False)

        config = LeaderboardConfig()
        assert config.url == _DEFAULT_URL
        assert config.timeout == float(_DEFAULT_TIMEOUT)
        assert config.mode == "auto"
        assert config.cors_origins == ["http://localhost", "http://127.0.0.1"]


class TestLeaderboardConfigUrlValidation:
    def test_invalid_url_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("AIRWAR_LEADERBOARD_URL", "not-a-valid-url")
        config = LeaderboardConfig()
        assert config.url == _DEFAULT_URL

    def test_empty_url_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("AIRWAR_LEADERBOARD_URL", "")
        config = LeaderboardConfig()
        assert config.url == _DEFAULT_URL

    def test_valid_url_is_preserved(self, monkeypatch):
        monkeypatch.setenv("AIRWAR_LEADERBOARD_URL", "http://example.com:9000/")
        config = LeaderboardConfig()
        assert config.url == "http://example.com:9000"

    def test_missing_scheme_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("AIRWAR_LEADERBOARD_URL", "example.com")
        config = LeaderboardConfig()
        assert config.url == _DEFAULT_URL


class TestLeaderboardConfigTimeoutValidation:
    def test_invalid_timeout_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("AIRWAR_LEADERBOARD_TIMEOUT", "abc")
        config = LeaderboardConfig()
        assert config.timeout == float(_DEFAULT_TIMEOUT)

    @pytest.mark.parametrize("bad_value", ["0", "-1", "30.1", "inf"])
    def test_out_of_range_timeout_falls_back_to_default(self, monkeypatch, bad_value):
        monkeypatch.setenv("AIRWAR_LEADERBOARD_TIMEOUT", bad_value)
        config = LeaderboardConfig()
        assert config.timeout == float(_DEFAULT_TIMEOUT)

    def test_valid_timeout_is_preserved(self, monkeypatch):
        monkeypatch.setenv("AIRWAR_LEADERBOARD_TIMEOUT", "5.5")
        config = LeaderboardConfig()
        assert config.timeout == 5.5


class TestLeaderboardConfigCorsOrigins:
    def test_default_cors_origins(self, monkeypatch):
        monkeypatch.delenv("AIRWAR_LEADERBOARD_CORS_ORIGINS", raising=False)
        config = LeaderboardConfig()
        assert config.cors_origins == ["http://localhost", "http://127.0.0.1"]

    def test_custom_cors_origins(self, monkeypatch):
        monkeypatch.setenv(
            "AIRWAR_LEADERBOARD_CORS_ORIGINS",
            "http://game.example.com, https://app.example.com ",
        )
        config = LeaderboardConfig()
        assert config.cors_origins == ["http://game.example.com", "https://app.example.com"]

    def test_wildcard_is_development_mode(self, monkeypatch):
        monkeypatch.setenv("AIRWAR_LEADERBOARD_CORS_ORIGINS", "*")
        config = LeaderboardConfig()
        assert config.cors_origins == ["*"]

    def test_empty_string_is_development_mode(self, monkeypatch):
        monkeypatch.setenv("AIRWAR_LEADERBOARD_CORS_ORIGINS", "")
        config = LeaderboardConfig()
        assert config.cors_origins == ["*"]
