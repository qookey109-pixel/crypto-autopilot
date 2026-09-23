#!/usr/bin/env python3
"""Fail closed before a queued Pages artifact can replace newer main content."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


SHA = re.compile(r"[0-9a-f]{40}\Z")
CONTENT_HASH = re.compile(r"[0-9a-f]{64}\Z")
PUBLISHED_HASH_URL = (
    "https://qookey109-pixel.github.io/crypto-autopilot/data/content-hash.txt"
)


def deployment_decision(
    *, expected_sha: str, current_main_sha: str, content_hash: str, published_hash: str
) -> str:
    if not SHA.fullmatch(expected_sha) or not SHA.fullmatch(current_main_sha):
        raise ValueError("invalid main commit SHA")
    if not CONTENT_HASH.fullmatch(content_hash):
        raise ValueError("invalid dashboard content hash")
    if expected_sha != current_main_sha:
        return "STALE_MAIN"
    if content_hash == published_hash:
        return "UNCHANGED_CONTENT"
    return "DEPLOY"


def read_current_main_sha(repository: str, token: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("invalid GitHub repository")
    if not token:
        raise ValueError("missing GitHub token")
    request = Request(
        f"https://api.github.com/repos/{repository}/git/ref/heads/main",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "qookey-dashboard-deploy-guard",
        },
    )
    with urlopen(request, timeout=10) as response:
        payload = json.load(response)
    return str(payload["object"]["sha"])


def read_published_hash() -> str:
    request = Request(
        PUBLISHED_HASH_URL,
        headers={"User-Agent": "qookey-dashboard-deploy-guard"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            return response.read(256).decode("ascii").strip()
    except HTTPError as exc:
        if exc.code == 404:
            return ""
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--content-hash", required=True)
    parser.add_argument("--github-output", type=Path, required=True)
    args = parser.parse_args()
    current_main_sha = read_current_main_sha(
        args.repository, os.environ.get("GITHUB_TOKEN", "")
    )
    # A stale artifact needs no Pages request; a current artifact needs one
    # final comparison because another run may have deployed while it waited.
    published_hash = (
        read_published_hash() if current_main_sha == args.expected_sha else ""
    )
    decision = deployment_decision(
        expected_sha=args.expected_sha,
        current_main_sha=current_main_sha,
        content_hash=args.content_hash,
        published_hash=published_hash,
    )
    with args.github_output.open("a", encoding="utf-8") as output:
        output.write(f"deploy_required={str(decision == 'DEPLOY').lower()}\n")
        output.write(f"decision={decision}\n")
    print(f"Dashboard deployment decision: {decision}")


if __name__ == "__main__":
    main()
