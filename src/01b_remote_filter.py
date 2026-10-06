#!/usr/bin/env python3
"""
01b_remote_filter.py: Online-Check. Nur aktiv, wenn im Profil "nur_online": true steht,
sonst gehen alle Treffer weiter und der Scorer bewertet den Ort (ort_fit).

Viele Anzeigen schreiben selten "100% remote", eher "online",
"per Zoom" oder "ortsunabhaengig". Deshalb:
  - Websuche-Treffer (Seiten, keine Anzeigen) -> immer behalten, der Scorer entscheidet
  - Anzeige mit is_remote oder Online-Signal  -> behalten
  - Anzeige ohne Online-Signal               -> raus (im Test waren das fast nur Praesenzstellen)
"online bewerben" zaehlt nicht als Online-Signal.

Input:  data/raw/jobs_YYYY-MM-DD.json
Output: data/filtered/jobs_filtered_YYYY-MM-DD.json + rejected_onsite_YYYY-MM-DD.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
FILTERED_DIR = ROOT / "data" / "filtered"
FILTERED_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_PATH = ROOT / "data" / os.environ.get("PROFILE_FILE", "profile.json")
TODAY = datetime.now().strftime("%Y-%m-%d")

ONLINE = re.compile(
    r"\b(remote|online|home[- ]?office|ortsunabh(ä|ae)ngig|virtuell|digital|per video|videocall|"
    r"zoom|von zu hause|work from (home|anywhere)|fjernarbejde|hjemmefra|online[- ]baseret)\b",
    re.IGNORECASE,
)
# ponytail: kleine Wortliste statt LLM-Pruefung; bei zu vielen falschen Drops hier nachschaerfen
ONSITE = re.compile(
    r"\b(vor ort|in pr(ä|ae)senz|anwesenheitspflicht|in unserer praxis|in unserer klinik|einsatzort|"
    r"hausbesuche|f(ü|ue)hrerschein|dienstwagen|on[- ]?site|in[- ]office|på stedet|fremmøde)\b",
    re.IGNORECASE,
)


APPLY_ONLINE = re.compile(r"online[- ]?bewerb\w*|bewerb\w*( sie sich| dich)? (jetzt )?online|online[- ]?formular", re.IGNORECASE)


def check(job: dict) -> tuple[bool, str]:
    if job.get("source_board") == "websuche" or job.get("is_remote"):
        return True, ""
    text = APPLY_ONLINE.sub(" ", f"{job.get('title', '')}\n{job.get('location', '')}\n{job.get('description', '')}")
    if ONLINE.search(text):
        return True, ""
    m = ONSITE.search(text)
    return False, f"nur Praesenz-Hinweis: '{m.group(0)}'" if m else "kein Online-Hinweis in der Anzeige"


def main() -> int:
    raw_path = RAW_DIR / f"jobs_{TODAY}.json"
    if not raw_path.exists():
        sys.exit(f"❌ {raw_path} fehlt, erst Crawler ausfuehren.")
    jobs = json.loads(raw_path.read_text())
    nur_online = json.loads(PROFILE_PATH.read_text()).get("nur_online", False) if PROFILE_PATH.exists() else False

    keep, rejected = [], []
    for job in jobs:
        ok, reason = check(job) if nur_online else (True, "")
        if ok:
            keep.append(job)
        else:
            rejected.append({**job, "reject_reason": reason})

    (FILTERED_DIR / f"jobs_filtered_{TODAY}.json").write_text(json.dumps(keep, indent=2, ensure_ascii=False))
    (FILTERED_DIR / f"rejected_onsite_{TODAY}.json").write_text(json.dumps(rejected, indent=2, ensure_ascii=False))
    print(f"✅ Online-Check: {len(keep)} behalten, {len(rejected)} raus (nur vor Ort oder ohne Online-Hinweis)")
    if not keep:
        print("⚠️  Keine neuen Treffer diese Woche. Der Radar zeigt weiter die Funde der letzten Wochen.")
    return 0  # nie abbrechen: leere Woche ist kein Fehler


def selftest() -> None:
    assert check({"title": "Projektleitung (m/w/d)", "description": "Abstimmungen per Zoom"})[0]
    assert not check({"title": "Sachbearbeitung", "description": "Hausbesuche mit Dienstwagen"})[0]
    assert check({"title": "Trainer", "description": "online oder vor Ort in Hamburg"})[0]
    assert not check({"title": "Teamassistenz", "description": "Bewerben Sie sich online"})[0]
    assert check({"source_board": "websuche", "description": "in unserer Praxis"})[0]
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
