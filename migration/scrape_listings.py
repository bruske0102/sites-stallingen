#!/usr/bin/env python3
"""Phase 1 polite listing scrape for stallingen.xyz (stallingen).

Reads three-segment listing URLs from migration/listing-urls.txt (or sitemap),
fetches at ~1 req/s with retries, writes:
  migration/scrape/raw/{provincie}--{plaats}--{slug}.html
  migration/scrape/normalized/{provincie}--{plaats}--{slug}.json
  src/content/stallingen/{provincie}--{plaats}--{slug}.json  (PHASE1_SCHEMA)

Resume-safe: skips URLs already present in normalized/ unless --force.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

BASE = "https://stallingen.xyz"
UA = "CursorMigrationBot/1.0 (+https://cursor.com; migration Phase1 listing scrape)"
ROOT = Path(__file__).resolve().parent
SITE = ROOT.parent
RAW = ROOT / "scrape" / "raw"
NORM = ROOT / "scrape" / "normalized"
CONTENT = SITE / "src" / "content" / "stallingen"
LISTING_URLS = ROOT / "listing-urls.txt"
SITEMAP_URLS = ROOT / "sitemap-urls.txt"
STATE = ROOT / "scrape" / "scrape-state.json"
MANIFEST = ROOT / "scrape" / "manifest.json"

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

SERVICE_HINTS = [
    ("Type", "fiets", re.compile(r"fiets|bromfiets|scooter", re.I)),
    ("Type", "auto", re.compile(r"auto|parkeer|garage", re.I)),
    ("Type", "boot", re.compile(r"boot|jacht|haven", re.I)),
    ("Type", "caravan", re.compile(r"caravan|camper", re.I)),
]



DAY_MAP = {
    "maandag": "ma",
    "dinsdag": "di",
    "woensdag": "wo",
    "donderdag": "do",
    "vrijdag": "vr",
    "zaterdag": "za",
    "zondag": "zo",
}


def listing_urls() -> list[str]:
    src = LISTING_URLS if LISTING_URLS.exists() else SITEMAP_URLS
    out: list[str] = []
    for line in src.read_text().splitlines():
        u = line.strip()
        if not u:
            continue
        parts = [x for x in urlparse(u).path.split("/") if x]
        if len(parts) == 3 and parts[0] in PROVS:
            if not u.endswith("/"):
                u += "/"
            out.append(u)
    # de-dupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def parts_of(url: str) -> tuple[str, str, str]:
    parts = [x for x in urlparse(url).path.split("/") if x]
    return parts[0], parts[1], parts[2]


def file_stem(url: str) -> str:
    p, pl, s = parts_of(url)
    return f"{p}--{pl}--{s}"


def decode_cfemail(hexstr: str) -> str | None:
    try:
        raw = bytes.fromhex(hexstr)
    except ValueError:
        return None
    if not raw:
        return None
    key = raw[0]
    return "".join(chr(b ^ key) for b in raw[1:])


def meta_content(html: str, name: str) -> str | None:
    m = re.search(
        rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']*)["\']',
        html,
        re.I,
    )
    if not m:
        m = re.search(
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']{re.escape(name)}["\']',
            html,
            re.I,
        )
    return unescape(m.group(1)).strip() if m else None


def itemprop(html: str, prop: str) -> str | None:
    # <meta itemprop="name" content="...">
    m = re.search(
        rf'<meta[^>]+itemprop=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']*)["\']',
        html,
        re.I,
    )
    if m:
        return unescape(m.group(1)).strip() or None
    # <span/a/div itemprop="x">text</...>
    m = re.search(
        rf'<(?:span|a|div|td|li)[^>]+itemprop=["\']{re.escape(prop)}["\'][^>]*>(.*?)</(?:span|a|div|td|li)>',
        html,
        re.I | re.S,
    )
    if m:
        text = re.sub(r"<[^>]+>", " ", m.group(1))
        text = unescape(re.sub(r"\s+", " ", text)).strip()
        return text or None
    return None


def strip_tags(html_frag: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", html_frag, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def parse_hours(html: str) -> dict[str, str] | None:
    hours: dict[str, str] = {}
    # e.g. Maandag: 09:00 - 17:00
    for day_nl, key in DAY_MAP.items():
        m = re.search(
            rf"{day_nl}\s*[:\-–]\s*([^\n<]{{2,40}})",
            html,
            re.I,
        )
        if m:
            val = unescape(m.group(1)).strip(" .;")
            val = re.sub(r"\s+", " ", val)
            if val and len(val) < 40:
                hours[key] = val
    return hours or None


def service_hints(text: str) -> dict[str, list[str]] | None:
    found: dict[str, list[str]] = {}
    for group, label, rx in SERVICE_HINTS:
        if rx.search(text):
            found.setdefault(group, [])
            if label not in found[group]:
                found[group].append(label)
    return found or None


def clean_title(title: str | None) -> str | None:
    if not title:
        return None
    t = title.strip()
    t = re.sub(r"^[ᐅ➤►\s]+", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t or None


def is_listing_html(html: str) -> bool:
    return 'itemtype="http://schema.org/LocalBusiness"' in html or "company-details" in html


def parse_listing(url: str, html: str, http_status: int) -> dict:
    provincie, plaats, slug = parts_of(url)
    naam = itemprop(html, "name")
    if not naam:
        t = clean_title(re.search(r"<title>([^<]+)", html, re.I).group(1) if re.search(r"<title>([^<]+)", html, re.I) else None)
        if t:
            # drop trailing phone/email often in title
            naam = re.split(r"\s{2,}|\s+\d{2,}", t, maxsplit=1)[0].strip() or t
    straat = itemprop(html, "streetAddress")
    postcode = itemprop(html, "postalCode")
    plaatsnaam = itemprop(html, "addressLocality")
    telefoon = itemprop(html, "telephone")
    if telefoon:
        telefoon = re.sub(r"\s+", " ", telefoon).strip()

    website = None
    m = re.search(r'itemprop=["\']url["\'][^>]*href=["\']([^"\']+)["\']', html, re.I)
    if not m:
        m = re.search(r'href=["\']([^"\']+)["\'][^>]*itemprop=["\']url["\']', html, re.I)
    if m:
        website = m.group(1).strip()
    if not website:
        m = re.search(
            r'<div class="label">\s*Website\s*</div>\s*<div class="value">\s*<a[^>]+href=["\']([^"\']+)["\']',
            html,
            re.I | re.S,
        )
        if m:
            website = m.group(1).strip()

    email = None
    cf = re.search(r'data-cfemail=["\']([0-9a-fA-F]+)["\']', html)
    if cf:
        email = decode_cfemail(cf.group(1))
    if not email:
        # sometimes plain in title/meta
        meta = meta_content(html, "description") or ""
        title = re.search(r"<title>([^<]+)", html, re.I)
        blob = meta + " " + (title.group(1) if title else "")
        em = re.search(r"[\w.+-]+@[\w.-]+\.\w+", blob)
        if em:
            email = em.group(0)

    lat = lon = None
    coords = re.findall(r"daddr=([\d.\-]+),([\d.\-]+)", html)
    if coords:
        try:
            lat = float(coords[0][0])
            lon = float(coords[0][1])
        except ValueError:
            lat = lon = None

    oms = None
    m = re.search(r"Omschrijving\s*</h1>\s*<p class=\"body\">(.*?)</p>", html, re.I | re.S)
    if m:
        oms = strip_tags(m.group(1))
        if not oms:
            oms = None

    openingstijden = parse_hours(html)

    rating_val = itemprop(html, "ratingValue")
    rating_count = itemprop(html, "ratingCount")
    beoordeling = None
    try:
        if rating_val is not None and rating_count is not None:
            gem = float(rating_val.replace(",", "."))
            aantal = int(float(rating_count.replace(",", ".")))
            if aantal > 0:
                beoordeling = {"gemiddeld": gem, "aantal": aantal}
    except ValueError:
        pass

    ids = re.findall(r"/bedrijf/(\d+)/", html)
    old_id = int(ids[0]) if ids else None

    title = clean_title(
        re.search(r"<title>([^<]+)", html, re.I).group(1) if re.search(r"<title>([^<]+)", html, re.I) else None
    )
    meta_description = meta_content(html, "description")

    status = "actief"
    low = html.lower()
    if http_status == 404 or not is_listing_html(html):
        status = "gesloten"
    elif re.search(r"\b(dit bedrijf is gesloten|niet meer actief|opgeheven)\b", low):
        status = "gesloten"

    # Off-niche: clear non-psychology businesses (careful; coaches with psych practice stay).
    name_blob = " ".join(
        x for x in [naam or "", slug.replace("-", " "), title or "", meta_description or "", oms or ""] if x
    ).lower()
    off_niche = re.compile(
        r"schilder|steiger|hovenier|aannemer|installat|autobedrijf|garage|kapsalon|restaurant|"
        r"\bmbo\b|hogeschool|universiteit|roc\b|voortgezet|\bmavo\b|\bhavo\b|\bvwo\b|"
        r"middelbare school|secundair|kinderdagverblijf|\bbso\b|gastouder|peuterspeelzaal|"
        r"fitness|sportschool|makelaar|notaris|advocaat|tandarts|"
        r"fysiotherapie|fysiotherapeut|dierenarts|homeopathie|"
        r"paardencoaching|hondencoach|astrologie|tarot|"
        r"gitaarles|muziekles|schildersbedrijf",
        re.I,
    )
    psych_ok = re.compile(
        r"stalling|psychologie|psychotherapie|psychotherapeut|psychiatr|"
        r"\bemdr\b|ggz|gz[- ]?psych|klinisch psych|neuropsych|"
        r"relatietherapie|gezinstherapie|kinderpsych|jeugdpsych|"
        r"psychosocia|psychomotor",
        re.I,
    )
    # Pure coaches / lifestyle without psychology signal
    coach_only = re.compile(
        r"(^|[^a-z])(life\s*)?coach(ing)?([^a-z]|$)|lifestyle|personal\s*training|"
        r"loopbaancoach|business\s*coach|mindfulness(?!.*psych)|yoga\s*studio",
        re.I,
    )
    if status == "actief" and off_niche.search(name_blob) and not psych_ok.search(name_blob):
        status = "gesloten"
    elif status == "actief" and coach_only.search(name_blob) and not psych_ok.search(name_blob):
        status = "gesloten"
    elif status == "actief" and not psych_ok.search(name_blob) and re.search(
        r"\b(schilder|dierenarts|fysiotherapie|gastouder|fitness)\b", name_blob
    ):
        status = "gesloten"


    hint_src = " ".join(x for x in [oms or "", title or "", meta_description or ""] if x)
    kenmerken = service_hints(hint_src)

    # lat/lon required by schema — fall back only if missing
    if lat is None or lon is None:
        lat = lat if lat is not None else 0.0
        lon = lon if lon is not None else 0.0

    if old_id is None:
        # stable synthetic id from path hash if missing
        old_id = abs(hash(f"{provincie}/{plaats}/{slug}")) % 900000 + 100000

    record = {
        "id": old_id,
        "slug": slug,
        "provincie": provincie,
        "plaats": plaats,
        "naam": naam or slug.replace("-", " ").title(),
        "straat": straat,
        "postcode": postcode,
        "plaatsnaam": plaatsnaam,
        "telefoon": telefoon,
        "email": email,
        "website": website or None,
        "lat": lat,
        "lon": lon,
        "omschrijving": oms,
        "openingstijden": openingstijden,
        "kenmerken": kenmerken,
        "beoordeling": beoordeling,
        "status": status,
        "oude_url": f"/{provincie}/{plaats}/{slug}/",
        "meta_title": title,
        "meta_description": meta_description,
        "_scrape": {
            "source_url": url,
            "http_status": http_status,
            "parsed_ok": is_listing_html(html),
            "has_coords": bool(coords),
        },
    }
    # drop nulls for optional empties? keep schema-aligned keys for content
    return record


def content_record(rec: dict) -> dict:
    """PHASE1 content file: drop scrape-only helpers; drop null email if absent."""
    out = {
        "id": rec["id"],
        "slug": rec["slug"],
        "provincie": rec["provincie"],
        "plaats": rec["plaats"],
        "naam": rec["naam"],
        "straat": rec["straat"],
        "postcode": rec["postcode"],
        "plaatsnaam": rec["plaatsnaam"],
        "telefoon": rec["telefoon"],
        "website": rec.get("website") or None,
        "lat": rec["lat"],
        "lon": rec["lon"],
        "status": rec["status"],
        "oude_url": rec["oude_url"],
    }
    if rec.get("email"):
        out["email"] = rec["email"]
    if rec.get("omschrijving"):
        out["omschrijving"] = rec["omschrijving"]
    if rec.get("openingstijden"):
        out["openingstijden"] = rec["openingstijden"]
    if rec.get("kenmerken"):
        out["kenmerken"] = rec["kenmerken"]
    if rec.get("beoordeling"):
        out["beoordeling"] = rec["beoordeling"]
    if rec.get("meta_title"):
        out["meta_title"] = rec["meta_title"]
    if rec.get("meta_description"):
        out["meta_description"] = rec["meta_description"]
    if not out.get("website"):
        out.pop("website", None)
    return out


def fetch(url: str, timeout: int = 30) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "nl-NL,nl;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200) or 200
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return status, raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body
    except Exception as e:
        raise RuntimeError(str(e)) from e


def fetch_with_retries(url: str, retries: int = 3, delay: float = 1.0) -> tuple[int, str]:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return fetch(url)
        except Exception as e:
            last_err = e
            time.sleep(delay * attempt)
    raise RuntimeError(f"fetch failed after {retries} tries: {last_err}")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 1 scrape all stalling listing pages")
    ap.add_argument("--limit", type=int, default=0, help="Max URLs (0 = all)")
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    ap.add_argument("--force", action="store_true", help="Re-fetch even if normalized exists")
    ap.add_argument("--no-content", action="store_true", help="Skip writing src/content/stallingen")
    ap.add_argument("--offset", type=int, default=0, help="Skip first N URLs")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    NORM.mkdir(parents=True, exist_ok=True)
    if not args.no_content:
        CONTENT.mkdir(parents=True, exist_ok=True)

    urls = listing_urls()
    if args.offset:
        urls = urls[args.offset :]
    if args.limit:
        urls = urls[: args.limit]

    print(f"[scrape] {len(urls)} listing URLs (delay={args.delay}s)", flush=True)

    ok = fail = skip = 0
    errors: list[dict] = []
    t0 = time.time()

    for i, url in enumerate(urls, 1):
        stem = file_stem(url)
        norm_path = NORM / f"{stem}.json"
        if norm_path.exists() and not args.force:
            skip += 1
            if i % 50 == 0 or i == len(urls):
                print(f"[scrape] {i}/{len(urls)} skip={skip} ok={ok} fail={fail}", flush=True)
            continue

        try:
            status, html = fetch_with_retries(url)
            (RAW / f"{stem}.html").write_text(html, encoding="utf-8")
            rec = parse_listing(url, html, status)
            write_json(norm_path, rec)
            if not args.no_content:
                write_json(CONTENT / f"{stem}.json", content_record(rec))
            if rec["_scrape"]["parsed_ok"]:
                ok += 1
            else:
                fail += 1
                errors.append({"url": url, "reason": "not_listing_html", "http_status": status})
        except Exception as e:
            fail += 1
            errors.append({"url": url, "reason": str(e)})
            print(f"[scrape] FAIL {url}: {e}", flush=True)

        if i % 25 == 0 or i == len(urls):
            elapsed = time.time() - t0
            print(
                f"[scrape] {i}/{len(urls)} ok={ok} fail={fail} skip={skip} elapsed={elapsed:.0f}s last={url}",
                flush=True,
            )
            write_json(
                STATE,
                {
                    "processed": i,
                    "ok": ok,
                    "fail": fail,
                    "skip": skip,
                    "last": url,
                    "elapsed_s": round(elapsed, 1),
                },
            )

        time.sleep(args.delay)

    # manifest summary
    norms = sorted(NORM.glob("*.json"))
    parsed_ok = 0
    with_website = 0
    with_phone = 0
    with_coords = 0
    actief = 0
    for p in norms:
        r = json.loads(p.read_text(encoding="utf-8"))
        if r.get("_scrape", {}).get("parsed_ok", True):
            parsed_ok += 1
        if r.get("website"):
            with_website += 1
        if r.get("telefoon"):
            with_phone += 1
        if r.get("_scrape", {}).get("has_coords") or (r.get("lat") and r.get("lon")):
            with_coords += 1
        if r.get("status") == "actief":
            actief += 1

    manifest = {
        "total_normalized": len(norms),
        "parsed_ok": parsed_ok,
        "actief": actief,
        "with_website": with_website,
        "with_phone": with_phone,
        "with_coords": with_coords,
        "run_ok": ok,
        "run_fail": fail,
        "run_skip": skip,
        "errors": errors[:50],
        "content_dir": str(CONTENT.relative_to(SITE)) if CONTENT.exists() else None,
    }
    write_json(MANIFEST, manifest)
    print(json.dumps(manifest, indent=2), flush=True)
    return 0 if fail == 0 or ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
