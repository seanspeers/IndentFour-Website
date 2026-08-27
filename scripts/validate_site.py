#!/usr/bin/env python3
"""Validate the rendered static site without third-party dependencies."""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


REQUIRED_PAGES = (
    Path("index.html"),
    Path("support/index.html"),
    Path("privacy/index.html"),
    Path("404.html"),
)
REQUIRED_FILES = (
    Path("CNAME"),
    Path(".nojekyll"),
    Path("robots.txt"),
    Path("sitemap.xml"),
    Path("site.webmanifest"),
    Path("favicon.ico"),
    Path("assets/site.css"),
    Path("assets/site.js"),
)
TRACKING_MARKERS = (
    "google-analytics.com",
    "googletagmanager.com",
    "gtag(",
    "plausible.io/js",
    "cdn.segment.com",
    "static.cloudflareinsights.com",
    "umami.is/script",
    "hotjar.com",
    "facebook.net/en_us/fbevents",
)
PLACEHOLDER_MARKERS = (
    "your_email",
    "your-domain",
    "your legal name",
    "lorem ipsum",
    "{{",
    "}}",
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.assets: list[str] = []
        self.images: list[dict[str, str]] = []
        self.h1_count = 0
        self.canonical: list[str] = []
        self.descriptions: list[str] = []
        self.jsonld_blocks: list[str] = []
        self._jsonld: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        if tag in {"link", "script", "img", "source"}:
            for attribute in ("href", "src"):
                if values.get(attribute):
                    self.assets.append(values[attribute])
            if values.get("srcset"):
                for candidate in values["srcset"].split(","):
                    self.assets.append(candidate.strip().split()[0])
        if tag == "img":
            self.images.append(values)
        if tag == "h1":
            self.h1_count += 1
        if tag == "link" and values.get("rel") == "canonical":
            self.canonical.append(values.get("href", ""))
        if tag == "meta" and values.get("name") == "description":
            self.descriptions.append(values.get("content", ""))
        if tag == "script" and values.get("type") == "application/ld+json":
            self._jsonld = []

    def handle_data(self, data: str) -> None:
        if self._jsonld is not None:
            self._jsonld.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._jsonld is not None:
            self.jsonld_blocks.append("".join(self._jsonld))
            self._jsonld = None


def local_target(site_root: Path, href: str) -> tuple[Path, str] | None:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        return None
    path = parsed.path
    if not path:
        return None
    relative = path.lstrip("/")
    candidate = site_root / relative
    if path.endswith("/"):
        candidate /= "index.html"
    return candidate, parsed.fragment


def check_site(site_root: Path) -> list[str]:
    errors: list[str] = []
    parsed_pages: dict[Path, PageParser] = {}

    for relative in (*REQUIRED_PAGES, *REQUIRED_FILES):
        if not (site_root / relative).exists():
            errors.append(f"Missing required file: {relative}")

    cname = site_root / "CNAME"
    if cname.exists() and cname.read_text(encoding="utf-8") != "indentfour.app\n":
        errors.append("CNAME must contain exactly indentfour.app followed by a newline")

    for relative in REQUIRED_PAGES:
        page = site_root / relative
        if not page.exists():
            continue
        text = page.read_text(encoding="utf-8")
        lowered = text.lower()
        for marker in TRACKING_MARKERS:
            if marker in lowered:
                errors.append(f"Tracking marker {marker!r} found in {relative}")
        for marker in PLACEHOLDER_MARKERS:
            if marker in lowered:
                errors.append(f"Placeholder marker {marker!r} found in {relative}")
        for match in re.findall(r"(?:src|href)=[\"'](http://[^\"']+)", text, re.I):
            errors.append(f"Insecure external URL in {relative}: {match}")

        parser = PageParser()
        parser.feed(text)
        parsed_pages[relative] = parser
        if parser.h1_count != 1:
            errors.append(f"{relative} has {parser.h1_count} h1 elements; expected 1")
        if len(parser.descriptions) != 1 or not parser.descriptions[0].strip():
            errors.append(f"{relative} must have one non-empty meta description")
        if relative != Path("404.html") and len(parser.canonical) != 1:
            errors.append(f"{relative} must have exactly one canonical URL")

        for image in parser.images:
            if "alt" not in image:
                errors.append(f"Image without alt text in {relative}: {image.get('src')}")
            if not image.get("width") or not image.get("height"):
                errors.append(f"Image without explicit dimensions in {relative}: {image.get('src')}")

        for block in parser.jsonld_blocks:
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(f"Invalid JSON-LD in {relative}: {exc}")

    for relative, parser in parsed_pages.items():
        for asset in parser.assets:
            parsed = urlsplit(asset)
            if parsed.scheme or parsed.netloc or asset.startswith("data:"):
                continue
            path = parsed.path
            if not path or path.startswith("#"):
                continue
            candidate = site_root / path.lstrip("/")
            if not candidate.exists():
                errors.append(f"Missing asset referenced by {relative}: {path}")

        for href in parser.links:
            if href.startswith(("mailto:", "tel:")):
                continue
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc:
                continue
            if not parsed.path and parsed.fragment:
                if parsed.fragment not in parser.ids:
                    errors.append(f"Missing fragment #{parsed.fragment} in {relative}")
                continue
            resolved = local_target(site_root, href)
            if resolved is None:
                continue
            target, fragment = resolved
            if not target.exists():
                errors.append(f"Broken internal link in {relative}: {href}")
                continue
            if fragment and target.suffix == ".html":
                target_relative = target.relative_to(site_root)
                target_parser = parsed_pages.get(target_relative)
                if target_parser is None:
                    target_parser = PageParser()
                    target_parser.feed(target.read_text(encoding="utf-8"))
                if fragment not in target_parser.ids:
                    errors.append(f"Missing target fragment in {relative}: {href}")

    index = parsed_pages.get(Path("index.html"))
    if index:
        schema_types = []
        for block in index.jsonld_blocks:
            try:
                schema_types.append(json.loads(block).get("@type"))
            except json.JSONDecodeError:
                pass
        for required_type in ("SoftwareApplication", "FAQPage"):
            if required_type not in schema_types:
                errors.append(f"Homepage is missing {required_type} JSON-LD")

    robots = site_root / "robots.txt"
    if robots.exists() and "https://indentfour.app/sitemap.xml" not in robots.read_text(encoding="utf-8"):
        errors.append("robots.txt does not reference the canonical sitemap")

    sitemap = site_root / "sitemap.xml"
    if sitemap.exists():
        sitemap_text = sitemap.read_text(encoding="utf-8")
        for url in (
            "https://indentfour.app/",
            "https://indentfour.app/support/",
            "https://indentfour.app/privacy/",
        ):
            if f"<loc>{url}</loc>" not in sitemap_text:
                errors.append(f"Sitemap is missing {url}")

    return errors


def main() -> None:
    site_root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors = check_site(site_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Validated {len(REQUIRED_PAGES)} pages and required static assets in {site_root}")


if __name__ == "__main__":
    main()
