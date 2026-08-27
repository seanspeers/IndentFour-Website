#!/usr/bin/env python3
"""Render the dependency-free Indent Four site from its small set of templates."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "src"
CONFIG_PATH = ROOT / "site.config.json"
PAGES = {
    TEMPLATE_DIR / "index.html": Path("index.html"),
    TEMPLATE_DIR / "support" / "index.html": Path("support/index.html"),
    TEMPLATE_DIR / "privacy" / "index.html": Path("privacy/index.html"),
    TEMPLATE_DIR / "404.html": Path("404.html"),
}
PUBLIC_ENTRIES = (
    "assets",
    ".nojekyll",
    "CNAME",
    "favicon.ico",
    "robots.txt",
    "sitemap.xml",
    "site.webmanifest",
)


def load_config() -> dict[str, str]:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    expected = {"siteUrl", "appStoreUrl", "supportEmail", "copyrightOwner"}
    missing = expected - data.keys()
    if missing:
        raise SystemExit(f"Missing site config values: {', '.join(sorted(missing))}")
    return {key: str(data[key]).strip() for key in expected}


def valid_app_store_url(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"apps.apple.com", "itunes.apple.com"}
        and bool(parsed.path.strip("/"))
    )


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))


def replacements(config: dict[str, str]) -> dict[str, str]:
    app_store_url = config["appStoreUrl"]
    has_app_store_url = valid_app_store_url(app_store_url)
    if app_store_url and not has_app_store_url:
        raise SystemExit("appStoreUrl must be an HTTPS apps.apple.com URL")

    support_email = config["supportEmail"]
    if support_email and not valid_email(support_email):
        raise SystemExit("supportEmail is not a valid email address")

    owner = config["copyrightOwner"]
    site_url = config["siteUrl"].rstrip("/")
    if site_url != "https://indentfour.app":
        raise SystemExit("siteUrl must remain https://indentfour.app")

    if has_app_store_url:
        escaped_url = html.escape(app_store_url, quote=True)
        primary_cta = (
            f'<a class="button button-primary nav-cta" href="{escaped_url}">'
            "Download on the App Store</a>"
        )
        footer_link = f'<a href="{escaped_url}">App Store</a>'
        jsonld_download = (
            f',\n        "downloadUrl": {json.dumps(app_store_url, ensure_ascii=False)}'
        )
    else:
        primary_cta = (
            '<span class="button release-status nav-cta">'
            "Coming to the App Store</span>"
        )
        footer_link = ""
        jsonld_download = ""

    if support_email:
        escaped_email = html.escape(support_email)
        support_block = (
            f'<p><a class="text-link" href="mailto:{escaped_email}">'
            f"{escaped_email}</a></p>"
        )
    else:
        support_block = (
            '<p class="contact-status">A support address will be published here '
            "before Indent Four is released.</p>"
        )

    copyright_line = (
        f'<p>© 2026 {html.escape(owner)}.</p>' if owner else ""
    )

    return {
        "{{APP_STORE_CTA}}": primary_cta,
        "{{FOOTER_APP_STORE_LINK}}": footer_link,
        "{{SUPPORT_EMAIL_BLOCK}}": support_block,
        "{{COPYRIGHT_LINE}}": copyright_line,
        "{{JSONLD_DOWNLOAD_URL}}": jsonld_download,
    }


def render_template(source: Path, destination: Path, values: dict[str, str]) -> None:
    rendered = source.read_text(encoding="utf-8")
    for token, value in values.items():
        rendered = rendered.replace(token, value)
    unresolved = sorted(set(re.findall(r"{{[A-Z0-9_]+}}", rendered)))
    if unresolved:
        raise SystemExit(
            f"Unresolved template tokens in {source}: {', '.join(unresolved)}"
        )
    rendered = "\n".join(line.rstrip() for line in rendered.splitlines()) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")


def copy_public_entry(name: str, output: Path) -> None:
    source = ROOT / name
    destination = output / name
    if source.resolve() == destination.resolve():
        return
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def build(output: Path) -> None:
    values = replacements(load_config())
    output.mkdir(parents=True, exist_ok=True)
    for source, relative_destination in PAGES.items():
        render_template(source, output / relative_destination, values)
    for entry in PUBLIC_ENTRIES:
        copy_public_entry(entry, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT,
        help="Destination directory (defaults to the repository root)",
    )
    args = parser.parse_args()
    build(args.output.resolve())


if __name__ == "__main__":
    main()
