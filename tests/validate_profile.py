#!/usr/bin/env python3
"""Validate Avery Quinn's GitHub profile identity, assets, and public links."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
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
RemoteChecker = Callable[[str], None]


def fail(message: str) -> None:
    raise AssertionError(message)


def check_remote(url: str) -> None:
    """Require one public URL to answer HEAD or a safe GET fallback."""

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


def validate_profile(
    *,
    root: Path = ROOT,
    check_links: bool = False,
    remote_checker: RemoteChecker = check_remote,
) -> tuple[int, int]:
    """Validate profile invariants and optionally check live link reachability."""

    resolved_root = root.resolve()
    readme = resolved_root / "README.md"
    text = readme.read_text(encoding="utf-8")

    for required in REQUIRED_TEXT:
        if required not in text:
            fail(f"README is missing required identity text: {required!r}")

    urls = {url.rstrip(".,") for url in URL_RE.findall(text)}
    missing_urls = REQUIRED_URLS - urls
    if missing_urls:
        fail(f"README is missing required public links: {sorted(missing_urls)}")

    image_sources = LOCAL_IMAGE_RE.findall(text)
    for source in image_sources:
        parsed = urlparse(source)
        if parsed.scheme or parsed.netloc:
            continue
        path = (resolved_root / source).resolve()
        if resolved_root not in path.parents:
            fail(f"local image escapes the repository: {source}")
        if not path.is_file():
            fail(f"local image does not exist: {source}")

    if check_links:
        for url in sorted(urls):
            remote_checker(url)

    return len(urls), len(image_sources)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="also verify live public-link reachability",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    url_count, image_count = validate_profile(check_links=args.check_links)
    link_scope = "live" if args.check_links else "declared"
    print(
        f"Validated profile identity, {url_count} {link_scope} public links, "
        f"and {image_count} local image reference(s)."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
