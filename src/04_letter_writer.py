#!/usr/bin/env python3
"""
04_letter_writer.py: Kurze Nachricht pro Top-Chance.

Stellenanzeige fuer eine Anstellung -> kurzes Anschreiben.
Alles andere (freie Mitarbeit, Plattform, Kooperation) -> kurze, persoenliche Kontakt-Anfrage.
Eigene Schreibregeln (Du/Sie, verbotene Woerter, Ton) kommen aus profile["schreib_regeln"].

Input:  data/runs/scored_YYYY-MM-DD.json
Output: data/runs/final_YYYY-MM-DD.json (+ latest.json), Top-Chancen mit "application"
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

RUNS_DIR = ROOT / "data" / "runs"
PROFILE_PATH = ROOT / "data" / os.environ.get("PROFILE_FILE", "profile.json")
TODAY = os.environ.get("RUN_DATE") or datetime.now().strftime("%Y-%m-%d")  # RUN_DATE: wie in 03_scorer.py
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:7b")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "ollama")
LETTER_MIN_SCORE = int(os.environ.get("LETTER_MIN_SCORE", "70"))

PROMPT = """Du schreibst ALS {name}, in der Ich-Form. {vorname} ist der Absender, die Organisation unten ist der Empfaenger.
{auftrag}

{vorname_gross}:
{bio}
Stationen: {stationen}
Was belegt ist: {belege}
Kontakt: {kontakt}

CHANCE:
Titel: {titel}
Organisation: {firma}
Was ist das: {was}
Warum es passt: {warum}
Huerden: {huerden}
Text (gekuerzt): {text}

Antworte AUSSCHLIESSLICH mit validem JSON:
{{
  "betreff": "kurz und konkret, max 70 Zeichen",
  "nachricht": "{laenge} Woerter, Ich-Form, in der Sprache der Anzeige. Beginne mit einer Anrede AN die Organisation (z.B. 'Liebes Team von ...,' oder 'Sehr geehrte Damen und Herren,'), Anredeform so wie die Organisation selbst schreibt, im Zweifel Sie. Dann ein konkreter Bezug zur Organisation, 2 bis 3 belegte Punkte aus dem Werdegang, eine klare, leichte Frage oder Bitte (z.B. nach einem kurzen Gespraech). Ende: Grussformel, dann '{name}' und die Kontaktzeile.",
  "linkedin_kurz": "max 280 Zeichen, persoenlich, kein Verkauf",
  "talking_points": ["3 Stichpunkte fuer ein erstes Gespraech"]
}}

REGELN:
- Warm, klar, direkt. Keine Floskeln wie "hiermit bewerbe ich mich".
- Keine Gedankenstriche (— oder –). Stattdessen Punkt oder Komma.
- Keine Werbe-Woerter wie Game-Changer, Transformation, Empowerment, authentisch.
- Nur Fakten aus dem Profil, nichts erfinden (keine Zahlen, Kunden oder Titel dazudichten).
- Keine Platzhalter in eckigen Klammern. Niemals {vorname} selbst anreden.
{eigene_regeln}"""


def looks_wrong(app: dict[str, Any], name: str) -> str | None:
    """Kleine Modelle schreiben gern aus Sicht der Firma an die Person oder lassen Platzhalter stehen."""
    text = str(app.get("nachricht", ""))
    vorname = re.escape(name.split()[0])
    if "[" in text or re.search(rf"^(liebe|lieber|hallo|hi|dear) {vorname}", text.strip(), re.I):
        return "falsche Perspektive oder Platzhalter"
    return None


def sign(app: dict[str, Any], p: dict[str, Any]) -> dict[str, Any]:
    """Fehlt der volle Name, haengt der Code die Kontaktzeile an, statt die Nachricht wegzuwerfen."""
    text = str(app.get("nachricht", "")).rstrip()
    if p["name"] not in text:
        line = p.get("contact_line") or ""
        if p["name"] not in line:
            line = f"{p['name']}\n{line}".strip()
        app["nachricht"] = f"{text}\n{line}"
    return app


DASH = re.compile(r"\s+[—–]\s+|\s*—\s*")  # Gedankenstriche raus, Zeitraeume wie 2009–2016 bleiben


def undash(obj):
    """Hard-Gate gegen Gedankenstriche, falls das Modell die Regel ignoriert."""
    if isinstance(obj, str):
        return DASH.sub(", ", obj)
    if isinstance(obj, dict):
        return {k: undash(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [undash(v) for v in obj]
    return obj


def write_request(job: dict[str, Any], p: dict[str, Any], client) -> dict[str, Any] | None:
    anstellung = (job.get("arbeitsmodell") or "").lower() == "anstellung"
    vorname = p["name"].split()[0]
    prompt = PROMPT.format(
        name=p["name"],
        vorname=vorname,
        vorname_gross=vorname.upper(),
        auftrag=("Schreibe ein kurzes Anschreiben fuer diese Stelle." if anstellung
                 else "Schreibe eine kurze, persoenliche Kontakt-Anfrage an diese Organisation."),
        laenge="150 bis 250" if anstellung else "90 bis 160",
        bio=p["bio_long"],
        stationen="; ".join(f"{s['period']} {s['role']} ({s['company']})" for s in p.get("stations", [])[:3]),
        belege="; ".join(p.get("belege", [])),
        kontakt=p.get("contact_line", ""),
        titel=job.get("title", ""),
        firma=job.get("company", ""),
        was=job.get("was_ist_das", ""),
        warum=job.get("reasoning", ""),
        huerden=", ".join(job.get("concerns") or []) or "(keine)",
        text=(job.get("description") or "")[:2500],
        eigene_regeln="\n".join(f"- {r}" for r in p.get("schreib_regeln", [])),
    )
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=1200,
        )
        result = undash(json.loads(resp.choices[0].message.content))
        problem = looks_wrong(result, p["name"])
        if problem:
            print(f"    ⚠️  Nachricht verworfen ({problem}), lieber keine als eine falsche")
            return None
        return sign(result, p)
    except Exception as e:
        print(f"    ⚠️  Nachricht fehlgeschlagen fuer '{job.get('title', '')[:50]}': {e}")
        return None


def selftest() -> None:
    assert looks_wrong({"nachricht": "Liebes Team,\n... Herzliche Gruesse\nVorname Nachname | a@b.de"}, "Vorname Nachname") is None
    assert looks_wrong({"nachricht": "Hallo Vorname, wir suchen dich ... Vorname Nachname"}, "Vorname Nachname")
    assert looks_wrong({"nachricht": "Sehr geehrte Damen und Herren, [Firma] ... Vorname Nachname"}, "Vorname Nachname")
    p = {"name": "Vorname Nachname", "contact_line": "Vorname Nachname | a@b.de"}
    assert sign({"nachricht": "Liebes Team, ... Viele Gruesse\nVorname"}, p)["nachricht"].endswith("Vorname\nVorname Nachname | a@b.de")
    assert sign({"nachricht": "... Gruesse\nVorname Nachname | a@b.de"}, p)["nachricht"].endswith("Gruesse\nVorname Nachname | a@b.de")
    assert sign({"nachricht": "... Gruesse"}, {"name": "Vorname Nachname", "contact_line": "a@b.de"})["nachricht"].endswith("Gruesse\nVorname Nachname\na@b.de")
    assert undash("Erfahrung — und mehr. 2009–2016") == "Erfahrung, und mehr. 2009–2016"
    print("selftest ok")


def main() -> int:
    from openai import OpenAI

    scored_path = RUNS_DIR / f"scored_{TODAY}.json"
    if not scored_path.exists():
        sys.exit(f"❌ {scored_path} fehlt, erst Scorer ausfuehren.")
    scored = json.loads(scored_path.read_text())
    profile = json.loads(PROFILE_PATH.read_text())
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    top = [j for j in scored if j.get("score", 0) >= LETTER_MIN_SCORE]
    print(f"=== Nachrichten {TODAY}: {len(top)} von {len(scored)} Treffern ab Score {LETTER_MIN_SCORE} ===")
    for i, job in enumerate(top, 1):
        print(f"  [{i}/{len(top)}] {job.get('company', '')}: {job.get('title', '')[:50]}")
        result = write_request(job, profile, client)
        if result:
            job["application"] = result
        time.sleep(0.2)

    out_path = RUNS_DIR / f"final_{TODAY}.json"
    out_path.write_text(json.dumps(scored, indent=2, ensure_ascii=False, default=str))
    latest = RUNS_DIR / "latest.json"
    latest.unlink(missing_ok=True)
    latest.symlink_to(out_path.name)
    print(f"✅ {sum(1 for j in scored if j.get('application'))} Nachrichten geschrieben → {out_path.name}")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
