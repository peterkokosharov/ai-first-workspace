#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Scrape build.nvidia.com/models for models with free endpoints.

Walks the listing pages (?page=1..N), finds model cards that advertise a
``free endpoint`` (usable with a free NVIDIA_API_KEY), visits each model's
detail page, and writes:

  kb/html/<page>-<slug>.html   -- raw detail-page HTML
  kb/md/<slug>.md              -- extracted alias, full name, endpoint

Skips models that are not LLMs or that carry a notice such as
"API access for this model is not available yet" /
"not open for programmatic access" / "no API key will authorize it".

Standard library only + vendored kikolib (http_client).
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from kikolib.http_client import client, HttpError  # noqa: E402

BASE = "https://build.nvidia.com"
LISTING_URL = BASE + "/models?page={page}"

# ---------------------------------------------------------------------------
# folder layout
# ---------------------------------------------------------------------------

KB = ROOT / "kb"
KB_HTML = KB / "html"
KB_MD = KB / "md"


def ensure_folders() -> None:
    KB_HTML.mkdir(parents=True, exist_ok=True)
    KB_MD.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# tiny HTML helpers (stdlib only)
# ---------------------------------------------------------------------------

class LinkExtractor(HTMLParser):
    """Collect <a href=...> text+href pairs."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._in_a = False
        self._href = ""
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._in_a = True
            self._href = ""
            self._text = []
            for k, v in attrs:
                if k == "href" and v:
                    self._href = v

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_a:
            self._in_a = False
            text = "".join(self._text).strip()
            if self._href and text:
                self.links.append((text, self._href))

    def handle_data(self, data: str) -> None:
        if self._in_a:
            self._text.append(data)


def fetch_text(url: str) -> str:
    """Fetch ``url`` and return decoded text (raises HttpError on failure)."""
    c = client()
    try:
        resp = c.request("GET", url, headers={"Accept": "text/html"})
        body = resp.read()
        return body.decode("utf-8", errors="replace")
    finally:
        c.close()


def save_bytes(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def save_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# listing page parsing
# ---------------------------------------------------------------------------

# Model detail URLs look like https://build.nvidia.com/<org>/<model-slug>
# or https://build.nvidia.com/models/<org>/<model-slug>
_MODEL_URL_RE = re.compile(r"^/(?:models/)?(?!explore|models)([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(?:/?)$")


def extract_model_links(listing_html: str) -> list[tuple[str, str]]:
    """Return [(slug, absolute_url)] of model detail links on the listing page."""
    parser = LinkExtractor()
    try:
        parser.feed(listing_html)
    except Exception:
        return []
    found: dict[str, str] = {}
    for text, href in parser.links:
        m = _MODEL_URL_RE.match(href)
        if not m:
            continue
        org, slug = m.group(1), m.group(2)
        full_slug = f"{org}/{slug}"
        if full_slug not in found:
            found[full_slug] = href if href.startswith("http") else BASE + href
    return list(found.items())


# ---------------------------------------------------------------------------
# detail page parsing
# ---------------------------------------------------------------------------

_UNAVAILABLE_PATTERNS = [
    re.compile(r"api access for this model is not available yet", re.I),
    re.compile(r"not open for programmatic access", re.I),
    re.compile(r"no api key will authorize it", re.I),
    re.compile(r"preview and playground use only", re.I),
]

_FREE_ENDPOINT_PATTERNS = [
    re.compile(r"free endpoint", re.I),
    re.compile(r"free.*api", re.I),
]


def is_unavailable(text: str) -> bool:
    return any(p.search(text) for p in _UNAVAILABLE_PATTERNS)


def has_free_endpoint(text: str) -> bool:
    return any(p.search(text) for p in _FREE_ENDPOINT_PATTERNS)


def extract_title(html: str) -> str:
    """Best-effort page title (full model name)."""
    m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if m:
        return unescape(m.group(1)).strip()
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.S)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def extract_endpoint(html: str) -> str | None:
    """Guess the chat-completions endpoint from the page."""
    m = re.search(r"https://integrate\.api\.nvidia\.com/v1/chat/completions", html)
    if m:
        return m.group(0)
    return None


def looks_like_llm(html: str) -> bool:
    """Heuristic: page mentions chat/completions or LLM-ish words."""
    low = html.lower()
    return any(
        token in low
        for token in (
            "chat/completions",
            "large language model",
            "llm",
            "text generation",
            "instruct",
        )
    )


# ---------------------------------------------------------------------------
# main scrape
# ---------------------------------------------------------------------------

def scrape_page(page: int) -> list[tuple[str, str]]:
    """Fetch one listing page and return [(slug, detail_url)] of free models."""
    url = LISTING_URL.format(page=page)
    print(f"[robota] fetching listing page {page}: {url}")
    html = fetch_text(url)

    # save raw listing html for reference
    save_bytes(KB_HTML / f"listing-page-{page}.html", html.encode("utf-8"))

    links = extract_model_links(html)
    print(f"[robota] found {len(links)} model links on page {page}")

    results: list[tuple[str, str]] = []
    for slug, detail_url in links:
        print(f"[robota]   visiting {slug}")
        try:
            detail_html = fetch_text(detail_url)
        except HttpError as exc:
            print(f"[robota]     skip {slug}: {exc}")
            continue

        # save raw detail html
        safe_slug = slug.replace("/", "_")
        save_bytes(KB_HTML / f"{safe_slug}.html", detail_html.encode("utf-8"))

        if is_unavailable(detail_html):
            print(f"[robota]     skip {slug}: unavailable notice")
            continue
        if not has_free_endpoint(detail_html):
            print(f"[robota]     skip {slug}: no free endpoint")
            continue
        if not looks_like_llm(detail_html):
            print(f"[robota]     skip {slug}: not an LLM")
            continue

        try:
            title = extract_title(detail_html)
            endpoint = extract_endpoint(detail_html)
            specs = extract_specs(detail_html)
            tags = extract_tags(detail_html)
        except Exception as exc:
            print(f"[robota]     skip {slug}: parse error: {exc}")
            continue
        entry = {
            "slug": slug,
            "title": title,
            "endpoint": endpoint,
            "source": detail_url,
            "specs": specs,
            "tags": tags,
        }
        results.append(entry)
        print(f"[robota]     OK {slug} | title={title!r} | endpoint={endpoint}")

    return results


def extract_specs(html: str) -> str:
    """Extract the Specifications paragraph from the sidebar, if present."""
    m = re.search(
        r'<p class="nv-text nv-text--body-regular-md[^>]*>(.*?)</p>',
        html, re.I | re.S,
    )
    if not m:
        return ""
    inner = re.sub(r"<[^>]+>", " ", m.group(1))
    return unescape(inner).strip()


def extract_tags(html: str) -> list[str]:
    """Extract label tags (Chat, Embedding, etc.) from the page."""
    tags: list[str] = []
    for m in re.finditer(
        r'href="/models\?label=([^"]+)"[^>]*><span[^>]*>(.*?)</span>',
        html, re.I | re.S,
    ):
        tag = unescape(m.group(2)).strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def write_markdown(
    slug: str,
    detail_url: str,
    title: str,
    endpoint: str | None,
    specs: str,
    tags: list[str],
) -> None:
    safe_slug = slug.replace("/", "_")
    md_path = KB_MD / f"{safe_slug}.md"
    lines = [
        f"# {title or slug}",
        "",
        f"- **alias**: {slug}",
        f"- **full name**: {title or slug}",
        f"- **source**: {detail_url}",
        f"- **endpoint**: {endpoint or 'not detected'}",
    ]
    if tags:
        lines.append(f"- **tags**: {', '.join(tags)}")
    if specs:
        lines.append("")
        lines.append("## Specifications")
        lines.append("")
        lines.append(specs)
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("Scraped from https://build.nvidia.com with `tools/robota.py`.")
    save_text(md_path, "\n".join(lines) + "\n")
    print(f"[robota] wrote {md_path}")


def write_index(entries: list[dict]) -> None:
    """Write a single index file with every model that has a free endpoint."""
    index_path = KB / "free_endpoints_index.md"
    lines = [
        "# Free Endpoint Models (NVIDIA build.nvidia.com)",
        "",
        "Models scraped from https://build.nvidia.com/models that advertise a "
        "free endpoint usable with a free NVIDIA_API_KEY.",
        "",
        f"Total: {len(entries)}",
        "",
        "| # | Alias | Full Name | Endpoint | Tags | Source |",
        "|---|-------|-----------|----------|------|--------|",
    ]
    for i, e in enumerate(entries, 1):
        tags = ", ".join(e.get("tags", []))
        lines.append(
            f"| {i} | {e['slug']} | {e['title']} | {e['endpoint']} | "
            f"{tags} | {e['source']} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("Generated by `tools/robota.py`.")
    save_text(index_path, "\n".join(lines) + "\n")
    print(f"[robota] wrote index {index_path} ({len(entries)} models)")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="robota.py",
        description="Scrape build.nvidia.com models with free endpoints into kb/.",
    )
    parser.add_argument(
        "--pages",
        default="1-2",
        help="page range to scrape, e.g. 1-2 or 1-5 (default: 1-2)",
    )
    args = parser.parse_args(argv)

    ensure_folders()

    m = re.match(r"(\d+)\s*-\s*(\d+)", args.pages)
    if not m:
        print("robota: --pages must be like 1-2", file=sys.stderr)
        return 2
    start, end = int(m.group(1)), int(m.group(2))

    total = 0
    entries: list[dict] = []
    for page in range(start, end + 1):
        try:
            results = scrape_page(page)
        except HttpError as exc:
            print(f"[robota] page {page} failed: {exc}")
            continue
        for entry in results:
            write_markdown(
                entry["slug"],
                entry["source"],
                entry["title"],
                entry["endpoint"],
                entry["specs"],
                entry["tags"],
            )
            entries.append(entry)
            total += 1

    write_index(entries)
    print(f"[robota] done. {total} model(s) written to kb/md/ and kb/html/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
