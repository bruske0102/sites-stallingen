#!/usr/bin/env python3
"""Check listing websites for dead/parked/spam (gambling etc.) redirects.

Writes src/data/websites.json keyed by listing id:
  { "status": "ok"|"dood"|"geparkeerd"|"spam"|"geblokkeerd"|"verhuisd"|"ander_domein"|"twijfel",
    "url"?: final url when status is verhuisd,
    "final"?: final url always when known,
    "reason"?: short note }

The Astro model only links websites with status in {ok, verhuisd, geblokkeerd}.
Spam/parked/dead/ander_domein/twijfel are never shown as clickable links.

Usage:
  python3 migration/check_websites.py
  python3 migration/check_websites.py --limit 20   # smoke test
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTENT = ROOT / "src" / "content" / "stallingen"
DEFAULT_OUT = ROOT / "src" / "data" / "websites.json"
DEFAULT_REPORT = ROOT / "migration" / "website-check-report.json"
UA = "Stalling-overzichtWebsiteCheck/1.0 (+https://stallingen.xyz; data quality)"

# Mutated by CLI
CONTENT = DEFAULT_CONTENT
OUT = DEFAULT_OUT
REPORT = DEFAULT_REPORT

PARK_HINTS = re.compile(
    r"domain\s+is\s+for\s+sale|buy\s+this\s+domain|parked\s+free|sedo\.com|godaddy\.com/park"
    r"|hugedomains|dan\.com|afternic|domainmarket|this\s+domain\s+may\s+be\s+for\s+sale"
    r"|website\s+coming\s+soon|future\s+home\s+of|default\s+web\s+site\s+page"
    r"|is\s+parked|parked\s+domain|domain\s+for\s+sale|this\s+domain\s+is\s+available",
    re.I,
)
PARK_HOSTS = {
    "mooiedomeinnaam.nl",
    "sedo.com",
    "dan.com",
    "afternic.com",
    "hugedomains.com",
    "godaddy.com",
    "domainmarket.com",
    "verwijzing.webreus.nl",
    "webreus.nl",
}
SPAM_HINTS = re.compile(
    r"\b(casino|gambling|sportsbook|betting|bookmaker|jackpot|poker|roulette|slots?"
    r"|gokken|wedden|wedkantoren?|online\s*casino|lucky\s*spin|crypto\s*casino"
    r"|viagra|cialis|pharmacy\s*online|adult\s*dating|escort\s*service"
    r"|forex\s*robot|binary\s*options?)\b",
    re.I,
)
BLOCK_HINTS = re.compile(
    r"attention\s+required|cf-browser-verification|just\s+a\s+moment|access\s+denied"
    r"|cloudflare|captcha|bot\s+detection|enable\s+javascript",
    re.I,
)
STOP_TOKENS = {
    "www",
    "http",
    "https",
    "nl",
    "com",
    "net",
    "org",
    "eu",
    "be",
    "de",
    "bv",
    "nv",
    "the",
    "and",
    "van",
    "der",
    "den",
    "het",
    "een",
    "stalling",
    "stallingen",
    "psychologie",
    "psychotherapie",
    "psychotherapeut",
    "praktijk",
    "therapie",
    "emdr",
    "ggz",
}

ctx = ssl.create_default_context()


def norm_url(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if not re.match(r"^https?://", raw, re.I):
        raw = "http://" + raw
    return raw


def host(url: str) -> str:
    try:
        h = urlparse(url).hostname or ""
    except Exception:
        return ""
    h = h.lower()
    if h.startswith("www."):
        h = h[4:]
    return h


def registrable(h: str) -> str:
    parts = h.split(".")
    if len(parts) >= 2:
        # crude: last two labels (enough for .nl / .com)
        if parts[-1] in {"uk", "au"} and len(parts) >= 3:
            return ".".join(parts[-3:])
        return ".".join(parts[-2:])
    return h


def fetch(url: str, timeout: float = 18.0) -> tuple[int, str, str, str]:
    """Return status, final_url, content_type, body_text_sample."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read(180_000)
            final = resp.geturl()
            status = getattr(resp, "status", 200) or 200
            ctype = (resp.headers.get("Content-Type") or "").lower()
            charset = resp.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, "replace")
            return status, final, ctype, text
    except urllib.error.HTTPError as e:
        raw = e.read(80_000) if e.fp else b""
        text = raw.decode("utf-8", "replace")
        final = e.geturl() if hasattr(e, "geturl") else url
        return e.code, final or url, "", text
    except Exception as e:
        return 0, url, "", str(e)


def tokens(s: str) -> set[str]:
    parts = re.split(r"[^a-z0-9]+", (s or "").lower())
    out = set()
    for p in parts:
        if len(p) < 3 or p in STOP_TOKENS:
            continue
        out.add(p)
    return out


def related_move(original: str, final: str, naam: str | None) -> bool:
    """True when the new host still looks like the same business."""
    o = tokens(host(original)) | tokens(registrable(host(original)))
    f = tokens(host(final)) | tokens(registrable(host(final)))
    n = tokens(naam or "")
    # shared brand token between old host and new host, or naam ↔ new host
    if o & f:
        return True
    if n & f:
        return True
    # e.g. old host contains brand that appears in new host as substring
    for a in o | n:
        for b in f:
            if len(a) >= 4 and (a in b or b in a):
                return True
    return False


def classify(original: str, status: int, final: str, text: str, naam: str | None = None) -> dict:
    o_host = host(original)
    f_host = host(final) if final else o_host
    f_reg = registrable(f_host)
    sample = unescape(re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.I))
    sample = re.sub(r"<style[\s\S]*?</style>", " ", sample, flags=re.I)
    sample = re.sub(r"<[^>]+>", " ", sample)
    sample = re.sub(r"\s+", " ", sample)[:8000]

    if status == 0:
        return {"status": "dood", "final": final, "reason": sample[:160] or "netwerkfout"}

    if status in {404, 410, 490, 521, 522, 523, 525, 526}:
        return {"status": "dood", "final": final, "reason": f"HTTP {status}"}

    if status in {401, 403, 429} or (status == 503 and BLOCK_HINTS.search(sample)):
        return {"status": "geblokkeerd", "final": final, "reason": f"HTTP {status}"}

    if f_reg in PARK_HOSTS or f_host in PARK_HOSTS or any(f_host.endswith("." + h) for h in PARK_HOSTS):
        return {"status": "geparkeerd", "final": final, "reason": f"parked host {f_host}"}

    if PARK_HINTS.search(sample) or PARK_HINTS.search(final or ""):
        return {"status": "geparkeerd", "final": final, "reason": "parked/for-sale signals"}

    if SPAM_HINTS.search(sample) or SPAM_HINTS.search(final or ""):
        return {"status": "spam", "final": final, "reason": "gambling/adult/pharma signals"}

    # redirect to totally different registrable domain
    if o_host and f_host and registrable(o_host) != f_reg:
        if SPAM_HINTS.search(f_host):
            return {"status": "spam", "final": final, "reason": f"redirect to spam host {f_host}"}
        if related_move(original, final, naam):
            return {
                "status": "verhuisd",
                "url": final if final.startswith("http") else original,
                "final": final,
                "reason": f"{o_host} → {f_host}",
            }
        return {
            "status": "ander_domein",
            "final": final,
            "reason": f"unrelated redirect {o_host} → {f_host}",
        }

    if status >= 400:
        return {"status": "twijfel", "final": final, "reason": f"HTTP {status}"}

    if status in {200, 201, 204, 301, 302, 303, 307, 308} or status < 400:
        if len(sample.strip()) < 40 and "html" not in (text[:200].lower()):
            return {"status": "twijfel", "final": final, "reason": "bijna lege response"}
        return {"status": "ok", "final": final}

    return {"status": "twijfel", "final": final, "reason": f"HTTP {status}"}


def load_listings() -> list[dict]:
    rows = []
    for path in sorted(CONTENT.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("website"):
            rows.append(
                {
                    "id": data["id"],
                    "naam": data.get("naam"),
                    "website": data["website"],
                    "slug": path.name,
                }
            )
    return rows


def check_one(row: dict) -> tuple[str, dict]:
    url = norm_url(row["website"])
    status, final, _ctype, text = fetch(url)
    # retry https if http failed hard
    if status == 0 and url.startswith("http://"):
        status, final, _ctype, text = fetch("https://" + url[len("http://") :])
        url = "https://" + url[len("http://") :]
    result = classify(url, status, final, text, naam=row.get("naam"))
    result["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    result["source"] = row["website"]
    return str(row["id"]), result


def main() -> None:
    global CONTENT, OUT, REPORT
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--only-status", default="", help="recheck ids currently in this status (comma)")
    ap.add_argument("--content", type=Path, default=DEFAULT_CONTENT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()
    CONTENT = args.content
    OUT = args.out
    REPORT = args.report

    listings = load_listings()
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}

    if args.only_status:
        want = {s.strip() for s in args.only_status.split(",") if s.strip()}
        listings = [r for r in listings if existing.get(str(r["id"]), {}).get("status") in want]

    if args.limit:
        listings = listings[: args.limit]

    print(f"checking {len(listings)} websites with {args.workers} workers…", flush=True)
    out = dict(existing)
    # When --only-status, merge into full report later from existing + new checks
    report = {"checked": [], "by_status": {}}

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(check_one, row): row for row in listings}
        for fut in as_completed(futs):
            row = futs[fut]
            try:
                key, result = fut.result()
            except Exception as e:
                key, result = str(row["id"]), {
                    "status": "dood",
                    "reason": f"exception: {e}",
                    "source": row["website"],
                }
            public = {"status": result["status"]}
            if result.get("url"):
                public["url"] = result["url"]
            if result.get("final") and result["status"] in {
                "verhuisd",
                "spam",
                "ander_domein",
                "twijfel",
                "geparkeerd",
                "dood",
            }:
                public["final"] = result["final"]
            if result.get("reason") and result["status"] != "ok":
                public["reason"] = result["reason"][:200]
            out[key] = public
            report["checked"].append(
                {
                    "id": row["id"],
                    "naam": row["naam"],
                    "website": row["website"],
                    **result,
                }
            )
            done += 1
            if done % 25 == 0 or done == len(listings):
                print(f"  {done}/{len(listings)}", flush=True)

    # prune ids no longer in content
    live_ids = {str(r["id"]) for r in load_listings()}
    out = {k: v for k, v in out.items() if k in live_ids}

    from collections import Counter

    c = Counter(v.get("status") for v in out.values())
    report["by_status"] = dict(c)
    report["spam"] = [x for x in report["checked"] if x.get("status") == "spam"]
    report["geparkeerd"] = [x for x in report["checked"] if x.get("status") == "geparkeerd"]
    report["ander_domein"] = [x for x in report["checked"] if x.get("status") == "ander_domein"]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("status counts:", dict(c))
    print(f"wrote {OUT}")
    print(f"wrote {REPORT}")
    if report["spam"]:
        print(f"SPAM hits: {len(report['spam'])}")
        for s in report["spam"][:20]:
            print(f"  - {s['id']} {s['naam']}: {s.get('website')} → {s.get('final')} ({s.get('reason')})")


if __name__ == "__main__":
    main()
