"""Tests for the PR-comment poster (M5, Track CC) -- no real network calls,
_api_request is monkeypatched throughout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import bench.post_pr_comment as poster


def test_skips_gracefully_outside_pr_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    md = tmp_path / "findings.md"
    md.write_text("no findings")
    monkeypatch.setattr("sys.argv", ["post_pr_comment.py", "--markdown-file", str(md)])
    assert poster.main() == 0
    assert "skipping comment post" in capsys.readouterr().out


def test_posts_new_comment_when_none_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 42}}))
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/widgets")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))

    calls: list[tuple[str, str, dict[str, str] | None]] = []

    def fake_api_request(url: str, token: str, method: str = "GET", body: dict[str, str] | None = None) -> Any:
        calls.append((url, method, body))
        if method == "GET":
            return []  # no existing comments
        return {"id": 1}

    monkeypatch.setattr(poster, "_api_request", fake_api_request)
    md = tmp_path / "findings.md"
    md.write_text("## ECDAT scan: 1 finding(s)")
    monkeypatch.setattr("sys.argv", ["post_pr_comment.py", "--markdown-file", str(md)])

    assert poster.main() == 0
    assert calls[-1][1] == "POST"
    assert calls[-1][0] == "https://api.github.com/repos/acme/widgets/issues/42/comments"
    assert poster._MARKER in calls[-1][2]["body"]  # type: ignore[index]


def test_updates_existing_comment_instead_of_posting_a_new_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 7}}))
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/widgets")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))

    calls: list[tuple[str, str, dict[str, str] | None]] = []

    def fake_api_request(url: str, token: str, method: str = "GET", body: dict[str, str] | None = None) -> Any:
        calls.append((url, method, body))
        if method == "GET":
            return [{"id": 99, "body": f"{poster._MARKER}\nold content"}]
        return {"id": 99}

    monkeypatch.setattr(poster, "_api_request", fake_api_request)
    md = tmp_path / "findings.md"
    md.write_text("## ECDAT scan: 0 finding(s)")
    monkeypatch.setattr("sys.argv", ["post_pr_comment.py", "--markdown-file", str(md)])

    assert poster.main() == 0
    assert calls[-1][1] == "PATCH"
    assert calls[-1][0] == "https://api.github.com/repos/acme/widgets/issues/comments/99"
