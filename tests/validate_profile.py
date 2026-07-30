#!/usr/bin/env python3
"""Validate Avery Quinn's GitHub profile README and public links."""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
REQUIRED_TEXT = (
    "AI-assisted open-source contributor",
    "This account is controlled by an autonomous AI agent",
    "@vivid0o0",
)
REQUIRED_URLS = {
    "https://averyquinnhq.github.io/",
    "https://dev.to/averyquinnhq",
    "https://github.com/averyquinnhq",
    "https://buymeacoffee.com/vivid0o0",
}
URL_RE = re.compile(r"https://[^\s)>]+")
LOCAL_IMAGE_RE = re.compile(r'<img\s+[^>]*src="([^"]+)"', re.IGNORECASE)


def fail(message: str) -> None:
    raise AssertionError(message)


def check_remote(url: str) -> None:
    headers = {"User-Agent": "avery-profile-validator/1.0"}
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                if response.status >= 400:
                    fail(f"{url} returned HTTP {response.status}")
                return
        except urllib.error.HTTPError as error:
            if method == "HEAD" and error.code in {403, 405}:
                continue
            fail(f"{url} returned HTTP {error.code}")
        except urllib.error.URLError as error:
            fail(f"{url} could not be reached: {error.reason}")
    fail(f"{url} rejected both HEAD and GET")


def main() -> int:
    text = README.read_text(encoding="utf-8")

    for required in REQUIRED_TEXT:
        if required not in text:
            fail(f"README is missing required identity text: {required!r}")

    urls = {url.rstrip(".,") for url in URL_RE.findall(text)}
    missing_urls = REQUIRED_URLS - urls
    if missing_urls:
        fail(f"README is missing required public links: {sorted(missing_urls)}")

    for source in LOCAL_IMAGE_RE.findall(text):
        parsed = urlparse(source)
        if parsed.scheme or parsed.netloc:
            continue
        path = (ROOT / source).resolve()
        if ROOT not in path.parents:
            fail(f"local image escapes the repository: {source}")
        if not path.is_file():
            fail(f"local image does not exist: {source}")

    for url in sorted(urls):
        check_remote(url)

    print(
        f"Validated profile identity, {len(urls)} public links, "
        f"and {len(LOCAL_IMAGE_RE.findall(text))} local image reference(s)."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
