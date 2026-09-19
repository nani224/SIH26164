"""Post (or update) a PR comment with the ECDAT findings table, using the
GitHub REST API directly via GITHUB_TOKEN (stdlib `urllib.request` only --
no third-party action, per the Track CC M5 brief).

Reads standard GitHub Actions env vars: GITHUB_TOKEN (must be exported by
the calling workflow step -- this script never reads it from anywhere
else, and never logs it), GITHUB_REPOSITORY (`owner/repo`), and the PR
number (from GITHUB_EVENT_PATH's pull_request.number, since
pull_request_target/pull_request events don't put it in a plain env var).

Idempotent: finds and edits its own previous comment (identified by a
hidden HTML marker) instead of piling up a new comment on every push to
the same PR.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

_MARKER = "<!-- ecdat-scan-comment -->"


def _api_request(url: str, token: str, method: str = "GET", body: dict[str, str] | None = None) -> object:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req) as resp:  # noqa: S310 -- fixed https://api.github.com host only
        return json.loads(resp.read())


def _find_pr_number() -> int | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return None
    event = json.loads(Path(event_path).read_text())
    pr = event.get("pull_request") or {}
    number = pr.get("number")
    return int(number) if number is not None else None


def _find_existing_comment_id(repo: str, pr_number: int, token: str) -> int | None:
    comments = _api_request(f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments", token)
    assert isinstance(comments, list)
    for comment in comments:
        if _MARKER in comment.get("body", ""):
            return int(comment["id"])
    return None


def post_comment(repo: str, pr_number: int, token: str, body: str) -> None:
    full_body = f"{_MARKER}\n{body}"
    existing_id = _find_existing_comment_id(repo, pr_number, token)
    if existing_id is not None:
        _api_request(
            f"https://api.github.com/repos/{repo}/issues/comments/{existing_id}",
            token, method="PATCH", body={"body": full_body},
        )
    else:
        _api_request(
            f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments",
            token, method="POST", body={"body": full_body},
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown-file", required=True, help="Path to the findings Markdown (from ci_scan.py)")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    pr_number = _find_pr_number()

    if not token or not repo or pr_number is None:
        print(
            "GITHUB_TOKEN / GITHUB_REPOSITORY / a pull_request event are required -- "
            "not running in a PR context, skipping comment post (this is not an error "
            "on a push-to-main run)."
        )
        return 0

    body = Path(args.markdown_file).read_text()
    try:
        post_comment(repo, pr_number, token, body)
    except urllib.error.HTTPError as exc:
        print(f"Failed to post PR comment: HTTP {exc.code} {exc.reason}")
        return 1
    print(f"Posted findings comment to {repo}#{pr_number}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
