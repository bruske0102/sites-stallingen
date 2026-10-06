#!/usr/bin/env python3
"""Phase 1c off-niche for Stallingen.xyz.

In scope: stalling, caravan-/camper-/bootstalling, self-storage, mini-opslag,
opslagbox, garagebox/garagepark.

Out: car garage, transport, verhuis, olie, fotografie, paving, koerier,
industrial without stalling/opslag in the name.

Rule: bij twijfel → gesloten. Name-only KEEP (body does not override).
HARD_JUNK in the name always wins.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT.parent / "src/content/stallingen"
NORM = ROOT / "scrape/normalized"
REPORT = ROOT / "OFF_NICHE_PASS.json"
MD = ROOT / "OFF_NICHE_TRIAGE.md"

STRONG_KEEP = re.compile(
    r"\bstalling\b|\bstallingen\b|self[- ]?storage|selfstorage|"
    r"\bopslag\b|opslagbox|opslagverhuur|fietsenstalling|"
    r"bootstalling|caravanstalling|camperstalling|"
    r"city\s*box|maxi\s*box|maxibox|storage\s*box|"
    r"containeropslag|boxopslag|garagepark|garagebox|"
    r"drop\s*and\s*go|space\s*winner|inboedelopslag|meubelopslag|"
    r"\bshurgard\b|\ballsafe\b|\bkubus\b|\beurobox\b|"
    r"mini\s*opslag|\bboxx\b",
    re.I,
)

HARD_JUNK = re.compile(
    r"metaalhandel|camping(?!\s*stalling)|kapsalon|makelaar|tandarts|fysio|"
    r"hovenier|schilder|autobedrijf|automobiel|autoprofi|"
    r"garagebedrijf|(?<!garage)(?<!box)\bgarage\b(?!park|box)|"
    r"sportschool|zwembad|fotografie|bestrating|bandenbeurs|"
    r"supermarkt|gemeente\b|architect|notaris|advocaat|dierenarts|"
    r"bouwbedrijf|aannemer|bouwfix|powder\s*technologies|graanbedrijf|"
    r"food\s*&\s*industry|koerier|"
    r"verhuisbedrijf|verhuizingen|verhuizing|"
    r"transportbedrijf|\btransport\b|logistiek|"
    r"\bolie\b|accu\s*centrale",
    re.I,
)


def name_blob(d: dict) -> str:
    slug = (d.get("slug") or "").replace("-", " ")
    return f"{d.get('naam') or ''} {d.get('slug') or ''} {slug}"


def should_close(d: dict) -> str | None:
    nb = name_blob(d)
    if HARD_JUNK.search(nb):
        return "hard junk name (garage/transport/verhuis/olie/…)"
    if STRONG_KEEP.search(nb):
        return None
    return "twijfel → gesloten (no stalling/opslag/self-storage in name)"


def main() -> None:
    closed = []
    reasons = Counter()
    actief = 0
    for path in sorted(CONTENT.glob("*.json")):
        d = json.loads(path.read_text())
        reason = should_close(d)
        if not reason:
            if d.get("status") != "actief" or d.get("_triage"):
                d["status"] = "actief"
                d.pop("_triage", None)
                path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
                npath = NORM / path.name
                if npath.exists():
                    nd = json.loads(npath.read_text())
                    nd["status"] = "actief"
                    nd.pop("_triage", None)
                    npath.write_text(json.dumps(nd, ensure_ascii=False, indent=2) + "\n")
            actief += 1
            continue
        d["status"] = "gesloten"
        d["_triage"] = {"reason": reason, "pass": "off-niche-1c-name"}
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")
        npath = NORM / path.name
        if npath.exists():
            nd = json.loads(npath.read_text())
            nd["status"] = "gesloten"
            nd["_triage"] = d["_triage"]
            npath.write_text(json.dumps(nd, ensure_ascii=False, indent=2) + "\n")
        closed.append({"naam": d.get("naam"), "reason": reason})
        reasons[reason] += 1

    report = {
        "total": actief + len(closed),
        "kept_actief": actief,
        "closed": len(closed),
        "counts": {"twijfel": 0, "closed": len(closed), "actief": actief},
        "reasons": dict(reasons),
        "samples": closed[:50],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    MD.write_text(
        "# Off-niche — Stallingen.xyz\n\n"
        "**Rule:** bij twijfel → gesloten. Name-only KEEP. HARD_JUNK always wins.\n"
        "**2026-10-06:** close garage/transport/verhuis/olie; keep stalling/opslag/self-storage in the name.\n\n"
        f"Actief {actief} · Gesloten {len(closed)} · twijfel=0\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in reasons.most_common())
        + "\n\n## Sample closed\n"
        + "\n".join(f"- {x['naam']}: {x['reason']}" for x in closed[:40])
        + "\n"
    )
    print(json.dumps(report["counts"], indent=2))
    print("reasons", dict(reasons))


if __name__ == "__main__":
    main()
