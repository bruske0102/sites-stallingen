#!/usr/bin/env python3
"""Polite Phase-0 crawler for stallingen.xyz.

- Max 1 request/second
- Clear user agent
- Respects robots Disallow patterns for */verwijderen/ and */wijzigen/
- Builds migration/url-inventory.csv incrementally

Adapted from sites/copyshop-overzicht/migration/crawl_inventory.py
"""

from __future__ import annotations

import csv
import re
import time
import urllib.error
import urllib.request
from collections import deque
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = "https://stallingen.xyz"
UA = "CursorMigrationBot/1.0 (+https://cursor.com; migration inventory)"
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "url-inventory.csv"
SITEMAP_URLS = ROOT / "sitemap-urls.txt"
STATE = ROOT / "crawl-state.txt"

PROVS = {
    "drenthe",
    "flevoland",
    "friesland",
    "gelderland",
    "groningen",
    "limburg",
    "noord-brabant",
    "noord-holland",
    "overijssel",
    "utrecht",
    "zeeland",
    "zuid-holland",
}

DISALLOW_RE = re.compile(r"/(verwijderen|wijzigen)/")
FIELDS = [
    "url",
    "page_type",
    "http_status",
    "title",
    "meta_description",
    "canonical",
    "h1",
    "in_sitemap",
    "final_url",
]

EXTRA_SEEDS = [
    f"{BASE}/",
    f"{BASE}/contact/",
    f"{BASE}/cookies/",
    f"{BASE}/zoeken/",
    f"{BASE}/zoeken/?q=amsterdam",
    f"{BASE}/bedrijf/toevoegen/",
    f"{BASE}/bedrijf/wijzigen/",
    f"{BASE}/blog/",
    f"{BASE}/kosten/",
    f"{BASE}/p/disclaimer/",
    f"{BASE}/p/support/",
]


def norm(url: str) -> str | None:
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith("http"):
        url = urljoin(BASE + "/", url)
    p = urlparse(url)
    if p.netloc not in ("stallingen.xyz", "www.stallingen.xyz"):
        return None
    path = p.path or "/"
    if DISALLOW_RE.search(path):
        return None
    # Keep search query for seed identity; drop other queries
    if p.path.rstrip("/") == "/zoeken" and p.query:
        q = p.query
        if not path.endswith("/"):
            path = path + "/"
        return f"https://stallingen.xyz{path}?{q}"
    if not path.endswith("/"):
        path = path + "/"
    return f"https://stallingen.xyz{path}"


def classify(url: str) -> str:
    path = urlparse(url).path.rstrip("/") or "/"
    parts = [x for x in path.split("/") if x]
    if path == "/":
        return "home"
    if parts[0] == "contact":
        return "static"
    if parts[0] == "cookies":
        return "static"
    if parts[0] == "zoeken":
        return "other"
    if parts[0] == "blog":
        return "blog"
    if parts[0] == "kosten":
        return "static"
    if parts[0] == "bedrijf":
        return "static"
    if parts[0] == "p":
        return "static"
    if parts[0] in PROVS:
        if len(parts) == 1:
            return "category"  # province
        if len(parts) == 2:
            return "location"
        if len(parts) == 3:
            return "listing"
        return "other"
    return "other"


def extract(html: str, base: str) -> dict:
    def one(pattern: str) -> str:
        m = re.search(pattern, html, re.I | re.S)
        return unescape(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""

    title = one(r"<title[^>]*>(.*?)</title>")
    desc = one(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']')
    if not desc:
        desc = one(r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']')
    canon = one(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](.*?)["\']')
    if not canon:
        canon = one(r'<link[^>]+href=["\'](.*?)["\'][^>]+rel=["\']canonical["\']')
    h1 = one(r"<h1[^>]*>(.*?)</h1>")
    h1 = re.sub(r"<[^>]+>", "", h1)
    links = set()
    for href in re.findall(r"""href=["']([^"']+)["']""", html, re.I):
        n = norm(urljoin(base, href))
        if n:
            links.add(n)
    return {
        "title": title[:500],
        "meta_description": desc[:800],
        "canonical": canon[:500],
        "h1": h1[:500],
        "links": links,
    }


def fetch(url: str) -> tuple[int, str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            final = resp.geturl()
            status = getattr(resp, "status", 200) or 200
            charset = resp.headers.get_content_charset() or "utf-8"
            html = raw.decode(charset, "replace")
            return status, html, final
    except urllib.error.HTTPError as e:
        raw = e.read() if e.fp else b""
        html = raw.decode("utf-8", "replace")
        return e.code, html, url
    except Exception as e:
        return 0, str(e), url


def load_done() -> set[str]:
    if not OUT.exists():
        return set()
    done = set()
    with OUT.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            done.add(row["url"])
    return done


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--mode",
        choices=["phase0", "full"],
        default="phase0",
        help="phase0: seeds+provinces+listings+sample locations; full: entire sitemap",
    )
    ap.add_argument("--location-sample", type=int, default=120)
    args = ap.parse_args()

    sitemap = set()
    sitemap_list: list[str] = []
    if SITEMAP_URLS.exists():
        for line in SITEMAP_URLS.read_text().splitlines():
            n = norm(line)
            if n:
                sitemap.add(n)
                sitemap_list.append(n)

    queue: deque[str] = deque()
    seen: set[str] = set(load_done())

    seeds = list(EXTRA_SEEDS)
    if args.mode == "full":
        seeds.extend(sitemap_list)
    else:
        # All provinces + all listings + sample of locations
        for u in sitemap_list:
            t = classify(u)
            if t in {"home", "category", "listing", "static"}:
                seeds.append(u)
        locations = [u for u in sitemap_list if classify(u) == "location"]
        # Prefer locations that have listings (from listing path prefixes)
        with_listing = set()
        for u in sitemap_list:
            if classify(u) == "listing":
                parts = [x for x in urlparse(u).path.split("/") if x]
                with_listing.add(f"{BASE}/{parts[0]}/{parts[1]}/")
        prioritized = [u for u in locations if u in with_listing]
        others = [u for u in locations if u not in with_listing]
        sample_n = max(0, args.location_sample)
        n_pri = min(len(prioritized), sample_n // 2)
        n_oth = min(len(others), sample_n - n_pri)
        seeds.extend(prioritized[:n_pri])
        seeds.extend(others[:n_oth])

    for u in seeds:
        n = norm(u)
        if n and n not in seen:
            queue.append(n)

    write_header = not OUT.exists()
    f = OUT.open("a", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    if write_header:
        writer.writeheader()

    last = 0.0
    processed = 0
    try:
        while queue:
            url = queue.popleft()
            if url in seen:
                continue
            seen.add(url)
            wait = 1.0 - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
            status, html, final = fetch(url)
            last = time.time()
            meta = (
                extract(html, final if final else url)
                if status and html
                else {
                    "title": "",
                    "meta_description": "",
                    "canonical": "",
                    "h1": "",
                    "links": set(),
                }
            )
            final_n = norm(final) or final
            row = {
                "url": url,
                "page_type": classify(url),
                "http_status": status,
                "title": meta["title"],
                "meta_description": meta["meta_description"],
                "canonical": meta["canonical"],
                "h1": meta["h1"],
                "in_sitemap": "yes" if urlparse(url)._replace(query="").geturl().rstrip("?") in sitemap or url.split("?")[0] in sitemap else "no",
                "final_url": final_n,
            }
            # Fix in_sitemap check for query URLs
            base_url = url.split("?")[0]
            if not base_url.endswith("/"):
                base_url += "/"
            row["in_sitemap"] = "yes" if base_url in sitemap else "no"
            writer.writerow(row)
            f.flush()
            processed += 1
            if processed % 25 == 0:
                STATE.write_text(
                    f"processed={processed} queued={len(queue)} seen={len(seen)} last={url}\n"
                )
                print(f"[crawl] {processed} done, queue={len(queue)} last={url}", flush=True)

            # Discover links from important pages only (phase0); fuller in full mode
            if status == 200 and (
                row["page_type"] in {"home", "category", "static", "listing"}
                or (row["page_type"] == "location" and processed <= 400)
            ):
                if args.mode == "full" or row["page_type"] in {"home", "category", "static"}:
                    for link in meta["links"]:
                        if link not in seen:
                            # In phase0, don't enqueue every thin location discovered
                            if args.mode == "phase0" and classify(link) == "location":
                                continue
                            queue.append(link)
    finally:
        f.close()
        STATE.write_text(f"done processed={processed} seen={len(seen)}\n")
        print(f"[crawl] finished processed={processed} seen={len(seen)}", flush=True)


if __name__ == "__main__":
    main()
