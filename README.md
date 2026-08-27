# Indent Four website

Production static website for [indentfour.app](https://indentfour.app), designed for GitHub Pages. It uses semantic HTML, one CSS design system, minimal JavaScript, and optimized derivatives of the shipping app icon and real App Store screenshots.

## Preview locally

The checked-in HTML files are ready to serve directly:

```sh
python3 -m http.server 8000
```

Open `http://localhost:8000/`. Root-relative asset paths require a local server rather than opening the HTML files directly from Finder.

After changing templates or release configuration, regenerate and validate the checked-in pages:

```sh
python3 scripts/build_site.py --output .
python3 scripts/validate_site.py .
```

## Editable release configuration

`site.config.json` is the single source of truth for release-dependent values:

- `appStoreUrl`: keep empty until the public listing exists; then use the full HTTPS `apps.apple.com` URL.
- `supportEmail`: keep empty until the public support address is confirmed.
- `copyrightOwner`: keep empty until the legal rights holder is confirmed.
- `siteUrl`: the canonical production origin and should remain `https://indentfour.app`.

The build script validates these values and renders the App Store links, support mail link, JSON-LD download URL, and copyright line only when the corresponding values are present. No placeholder identity is published.

## Images

Optimized AVIF and WebP files plus PNG fallbacks are committed under `assets/`. They were made from the real Indent Four icon and screenshots. `scripts/prepare_assets.py` records the source locations and can regenerate them on the original production Mac; CI does not depend on those external paths.

## GitHub Pages deployment

`.github/workflows/pages.yml` builds into `_site`, runs the static validator, uploads the Pages artifact, and deploys it with the official GitHub Pages actions. It runs on pushes to `main` and can also be started manually. The deploy job requests only `pages: write` and `id-token: write`; repository contents are read-only.

In the GitHub repository:

1. Open **Settings → Pages** and choose **GitHub Actions** as the source.
2. Set the custom domain to `indentfour.app`. The root `CNAME` file is also kept in source and copied into every artifact.
3. Configure the apex and optional `www` DNS records using GitHub’s current [custom-domain instructions](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site). Use the values shown by GitHub and the DNS provider; do not copy stale DNS values from third-party articles.
4. When GitHub finishes provisioning the certificate, enable **Enforce HTTPS**. GitHub documents the process in [Securing your GitHub Pages site with HTTPS](https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https).

GitHub also recommends [verifying the custom domain](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/verifying-your-custom-domain-for-github-pages) on the owning account or organization before publication.

## Pre-publication checklist

- Confirm the App Store URL, support email, and legal copyright owner; update `site.config.json`, rebuild, and commit the rendered pages.
- Create or connect the GitHub repository and push the `main` branch.
- Enable Pages with GitHub Actions, set the custom domain, complete DNS, and enable HTTPS.
- Re-run the visual and accessibility audits after any release copy or configuration change.
