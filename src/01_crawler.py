#!/usr/bin/env python3
"""
01_crawler.py: Chancen-Suche (Stellen, Plattformen, Kooperationen).

Zwei Quellen, beide aus profile["search_terms"]:
  1. jobspy          LinkedIn + Indeed (weitere Seiten siehe QUELLEN.md), pro Suchbegriff eigenes Land
  2. firecrawl_search Websuche ueber Firecrawl (braucht FIRECRAWL_API_KEY, kostet Credits)

Schon gesehene Links (data/seen_urls.json, pflegt 03_scorer) werden uebersprungen,
damit jede Woche nur Neues bewertet wird und keine Credits doppelt verbraucht werden.

Output: data/raw/jobs_YYYY-MM-DD.json
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

PROFILE_PATH = ROOT / "data" / os.environ.get("PROFILE_FILE", "profile.json")
SEEN_PATH = ROOT / "data" / "seen_urls.json"
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now().strftime("%Y-%m-%d")
# ponytail: Scrape-Deckel schuetzt die Firecrawl-Credits (1 Credit pro Seite), per .env anpassbar
SCRAPE_MAX = int(os.environ.get("FIRECRAWL_SCRAPE_MAX", "12"))
SEARCH_LIMIT = int(os.environ.get("FIRECRAWL_SEARCH_LIMIT", "8"))
# Standard-Seiten fuer jobspy; z.B. JOBSPY_SITES=linkedin wenn Indeed im Netz blockiert ist
JOBSPY_SITES = os.environ.get("JOBSPY_SITES", "linkedin,indeed").split(",")


def load_json(path: Path, default):
    return json.loads(path.read_text()) if path.exists() else default


def kill_by_terms(text: str, kill_terms: list[str]) -> str | None:
    lower = (text or "").lower()
    for term in kill_terms:
        if re.search(rf"\b{re.escape(term.lower())}\b", lower):
            return term
    return None


def clean(v: Any) -> str:
    """pandas liefert fehlende Werte als NaN, die sonst als 'nan' im Radar landen."""
    return "" if v is None or (isinstance(v, float) and v != v) else str(v)


PRO = {"yearly": "pro Jahr", "monthly": "pro Monat", "weekly": "pro Woche", "daily": "pro Tag", "hourly": "pro Stunde"}


def salary_text(row) -> str:
    lo, hi = clean(row.get("min_amount")), clean(row.get("max_amount"))
    if not lo:
        return ""
    zahl = lambda v: f"{float(v):,.0f}".replace(",", ".")  # 52000 -> 52.000
    interval = clean(row.get("interval"))
    return f"{zahl(lo)}{f'-{zahl(hi)}' if hi else ''} {clean(row.get('currency'))} {PRO.get(interval, interval)}".strip()


def too_old(posted: Any, max_age_days: int = 45) -> bool:
    try:
        dt = datetime.fromisoformat(str(posted).split("T")[0])
        return (datetime.now() - dt).days > max_age_days
    except (ValueError, TypeError):
        return False


# ----------------------------------------------------------------------------
# Quelle 1: jobspy (LinkedIn + Indeed)
# ----------------------------------------------------------------------------


def crawl_jobspy(entries: list[dict[str, Any]], profile: dict[str, Any], seen: set[str]) -> list[dict[str, Any]]:
    try:
        from jobspy import scrape_jobs
    except ImportError:
        print("⚠️  jobspy nicht installiert, ueberspringe LinkedIn/Indeed")
        return []

    kill_terms = profile.get("ausschluss_woerter", [])
    avoid = [a.lower() for a in profile.get("avoid_companies", [])]
    out: list[dict[str, Any]] = []

    for e, site in [(e, s) for e in entries for s in e.get("sites", JOBSPY_SITES)]:
        # Pro Seite einzeln: faellt Indeed aus (Timeout/403), bleiben die LinkedIn-Treffer erhalten.
        # LinkedIn versteht nur englische Ortsnamen ("Germany", nicht "Deutschland").
        print(f"  · {site} '{e['term']}' ({e.get('location', '-')})")
        try:
            df = scrape_jobs(
                site_name=[site],
                search_term=e["term"],
                location=e.get("location", ""),
                country_indeed=e.get("country_indeed", "germany"),
                is_remote=e.get("is_remote", False),
                results_wanted=15,
                hours_old=24 * 30,
                fetch_description=True,
                verbose=0,
            )
        except Exception as ex:
            print(f"    ⚠️  {site} Fehler: {str(ex)[:120]}")
            continue
        if df is None or df.empty:
            continue

        for _, row in df.iterrows():
            url = clean(row.get("job_url"))
            title = clean(row.get("title"))
            company = clean(row.get("company"))
            description = clean(row.get("description"))
            if not url or url in seen:
                continue
            if kill_by_terms(title + "\n" + description[:2000], kill_terms):
                continue
            if any(a in company.lower() for a in avoid) or too_old(row.get("date_posted")):
                continue
            out.append({
                "id": f"{row.get('site') or 'jobspy'}-{row.get('id') or abs(hash(url))}",
                "title": title,
                "company": company,
                "location": clean(row.get("location")),
                "url": url,
                "description": description,
                "salary": salary_text(row),
                # Nur der Wert der Jobboerse zaehlt. LinkedIns Remote-Suche liefert auch Hybrid- und Praesenzstellen.
                "is_remote": str(row.get("is_remote")) == "True",  # numpy.bool_ und NaN sicher
                "posted_date": clean(row.get("date_posted")),
                "source_board": clean(row.get("site")) or "jobspy",
                "search_term": e["term"],
                "bucket": e.get("kategorie", "ausschreibung"),
            })
    return out


# ----------------------------------------------------------------------------
# Quelle 2: Firecrawl-Websuche (firecrawl-py >= 4, v2-API)
# ----------------------------------------------------------------------------


def crawl_firecrawl_search(entries: list[dict[str, Any]], profile: dict[str, Any], seen: set[str]) -> list[dict[str, Any]]:
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("⚠️  FIRECRAWL_API_KEY fehlt, Websuche wird uebersprungen (siehe README.md)")
        return []
    try:
        from firecrawl import Firecrawl
    except ImportError:
        print("⚠️  firecrawl-py nicht installiert")
        return []

    # Ohne timeout wartet requests endlos: ein Lauf hing so 33 Stunden und blockierte alle Folgelaeufe.
    fc = Firecrawl(api_key=api_key, timeout=120)
    kill_terms = profile.get("ausschluss_woerter", [])
    hits: dict[str, dict[str, Any]] = {}

    for e in entries:
        print(f"  · Firecrawl-Suche '{e['query']}'")
        try:
            res = fc.search(e["query"], limit=SEARCH_LIMIT, sources=["web"], tbs="qdr:m")
        except Exception as ex:
            print(f"    ⚠️  Firecrawl Fehler: {ex}")
            continue
        for r in res.web or []:
            url = getattr(r, "url", "") or ""
            if not url or url in seen or url in hits:
                continue
            title = getattr(r, "title", "") or ""
            snippet = getattr(r, "description", "") or ""
            if kill_by_terms(f"{title}\n{snippet}", kill_terms):
                continue
            hits[url] = {
                "id": f"web-{abs(hash(url))}",
                "title": title,
                "company": re.sub(r"^www\.", "", url.split("/")[2]) if url.count("/") >= 2 else "",
                "location": "online",
                "url": url,
                "description": snippet,
                "salary": "",
                "is_remote": False,
                "posted_date": "",
                "source_board": "websuche",
                "search_term": e["query"],
                "bucket": e.get("kategorie", "ausschreibung"),
            }

    # Nur die ersten SCRAPE_MAX neuen Treffer ganz lesen, der Rest behaelt den Such-Ausschnitt.
    # Diese Seiten liest Firecrawl nicht (Fehler kostet trotzdem einen Abruf-Platz).
    unlesbar = ("instagram.com", "reddit.com", "linkedin.com/in/", "facebook.com", "tiktok.com")
    lesbar = [i for i in hits.values() if not any(u in i["url"] for u in unlesbar)]
    for n, item in enumerate(lesbar[:SCRAPE_MAX]):
        if n:
            time.sleep(7)  # ponytail: Free-Plan erlaubt ~10 Abrufe/Minute; bei bezahltem Plan Pause senken
        try:
            doc = fc.scrape(item["url"], formats=["markdown"], only_main_content=True)
            item["description"] = (doc.markdown or item["description"])[:6000]
        except Exception as ex:
            print(f"    ⚠️  Scrape Fehler {item['url'][:60]}: {ex}")
    return list(hits.values())


def main() -> int:
    print(f"=== Crawler Start: {TODAY} ===")
    if not PROFILE_PATH.exists():
        sys.exit(f"❌ {PROFILE_PATH} fehlt.")
    profile = json.loads(PROFILE_PATH.read_text())
    seen = set(load_json(SEEN_PATH, []))
    st = profile.get("search_terms", {})
    print(f"Profil: {profile['name']} · schon gesehen: {len(seen)} Links")

    print("\n→ LinkedIn + Indeed")
    jobs = crawl_jobspy(st.get("jobspy", []), profile, seen)
    print(f"   {len(jobs)} neue Treffer")

    print("\n→ Firecrawl-Websuche")
    web = crawl_firecrawl_search(st.get("firecrawl_search", []), profile, seen)
    print(f"   {len(web)} neue Treffer")

    deduped = list({j["url"]: j for j in jobs + web}.values())
    out_path = RAW_DIR / f"jobs_{TODAY}.json"
    out_path.write_text(json.dumps(deduped, indent=2, ensure_ascii=False, default=str))
    print(f"\n✅ {len(deduped)} neue Treffer → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
