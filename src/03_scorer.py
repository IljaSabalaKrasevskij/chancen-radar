#!/usr/bin/env python3
"""
03_scorer.py: Passt die Chance zur Person im Profil? Score 0-100 plus Erklaerung auf Deutsch.

Input:  data/filtered/jobs_filtered_YYYY-MM-DD.json (Fallback: data/raw/jobs_...)
Output: data/runs/scored_YYYY-MM-DD.json (absteigend nach Score)
        data/seen_urls.json (bewertete Links, damit der Crawler sie naechste Woche ueberspringt)

Die fuenf Dimensionen sind fest (Namen nicht aendern), ihre Gewichte kommen aus profile["scorer_weights"],
die persoenlichen Regeln aus profile["scoring_notes"].
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

DATA = ROOT / "data"
RUNS_DIR = DATA / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_PATH = DATA / os.environ.get("PROFILE_FILE", "profile.json")
SEEN_PATH = DATA / "seen_urls.json"

TODAY = os.environ.get("RUN_DATE") or datetime.now().strftime("%Y-%m-%d")  # RUN_DATE=JJJJ-MM-TT: Lauf eines anderen Tages nachholen
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5:7b")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "ollama")

PROMPT = """Du pruefst, ob eine gefundene Chance (Stellenanzeige, Plattform, Kooperation oder Webseite) zu {vorname} passt.

PERSON:
{profil}

GEWICHTE (Maximalpunkte je Dimension, Summe 100):
{gewichte}

SO BEWERTEST DU (Standard sind volle Punkte, abziehen nur mit einem Grund aus dem Text):
  thema_fit: Kernthemen voll, nahe Themen etwa die Haelfte, fremdes Thema wenig, Tabu-Thema 0.
  qualifikation_fit: voll, wenn {vorname} die Hauptaufgaben kann. 0 nur, wenn der Text ausdruecklich etwas verlangt, das unter "Fehlt" steht.
  ort_fit: voll bei remote oder einem Ort, der zum Profil passt. 0 nur bei Praesenzpflicht an einem Ort, an dem {vorname} nicht arbeiten kann.
  arbeitsmodell_fit: voll, wenn die Art der Arbeit zu "Sucht" passt. 0 nur, wenn sie dort ausgeschlossen ist.
  sprache_markt: voll, wenn {vorname} die Arbeitssprache spricht, sonst 0.
"Fehlt" beschreibt {vorname}, nicht die Stelle. Eine Anforderung zaehlt nur, wenn sie wirklich im Text steht.

REGELN VON {vorname} (gelten nur, wenn der Text den Fall wirklich zeigt):
{regeln}

GEFUNDENE CHANCE:
Titel: {titel}
Organisation/Seite: {firma}
Ort: {ort}
Remote laut Jobboerse: {remote}
Quelle: {quelle}
Automatisch im Text erkannt: {hinweise}
Text (gekuerzt): {text}

Die erkannten Hinweise sind echte Fundstellen im Text. "K.o.-Verdacht" heisst: pruefe genau, ob das eine Pflicht ist.

Antworte AUSSCHLIESSLICH mit validem JSON, alle Texte auf Deutsch, einfach und ohne Fachchinesisch:
{{
  "score": 0-100,
  "breakdown": {{{breakdown_keys}}},
  "was_ist_das": "1-2 einfache Saetze: Was ist das und was wuerde {vorname} dort tun?",
  "reasoning": "2-3 Saetze: warum passt es oder warum nicht. Konkret mit Bezug auf das Profil.",
  "matched_strengths": ["was von {vorname} hier zaehlt, max 3"],
  "concerns": ["Huerden oder Risiken, sonst leer"],
  "arbeitsmodell": "freiberuflich|Anstellung|Kooperation|Listing|unklar",
  "ortsunabhaengig": "ja|wahrscheinlich|nein|unklar",
  "naechster_schritt": "1 Satz: was {vorname} als Erstes tun sollte",
  "recommendation": "jetzt_angehen|pruefen|eher_nicht"
}}

WICHTIG: Sei kritisch. Jede breakdown-Zahl hoechstens ihr Gewicht. Keine Gedankenstriche (—). Nichts erfinden, was nicht im Text steht.
"""


# ponytail: Regex-Hinweise statt groesserem Modell. Im Test uebersah qwen2.5:7b "ortsunabhaengig"
# und gab der besten Anzeige 30 Punkte; qwen3:8b und gemma4 lieferten leeres JSON (Denk-Tokens).
HINWEISE = {
    "Online": re.compile(r"ortsunabh(ä|ae)ngig|remote|home[- ]?office|online[- ]?(coaching|beratung|sitzung|kurs)|per video|videoplattform|zoom|von zu hause|work from (home|anywhere)", re.I),
    "Freiberuflich": re.compile(r"freiberuflich|selbstst(ä|ae)ndig|honorarbasis|auf honorar|freelance|freie mitarbeit", re.I),
    "Anstellung": re.compile(r"festanstellung|unbefristet|sozialversicherungspflichtig|vollzeit|full[- ]time", re.I),
    "Teilzeit": re.compile(r"teilzeit|part[- ]time", re.I),
}

# Beitraege und Profile in sozialen Netzen sind keine Chancen (die Suche liefert nur einen Ausschnitt, kein Angebot):
# nicht bewerten. Wer eines dieser Netze als Quelle will, nimmt es hier heraus. "linkedin.com/jobs" bleibt bewusst frei.
SOZIAL = ("facebook.com", "instagram.com", "tiktok.com", "reddit.com", "linkedin.com/posts", "linkedin.com/in/")


def ist_sozial(url: str) -> bool:
    return any(s in url for s in SOZIAL)


def save_json(path: Path, data: Any, **kw) -> None:
    """Erst in eine Nebendatei, dann umbenennen: bricht der Lauf mitten im Schreiben ab, bleibt keine halbe Datei zurueck."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, default=str, **kw))
    tmp.replace(path)


def hinweise(text: str, ko_woerter: list[str] | tuple = ()) -> str:
    """ko_woerter aus dem Profil: Pflicht-Anforderungen, die die Person nicht erfuellt (z.B. Approbation, Fuehrerschein)."""
    rx = dict(HINWEISE)
    if ko_woerter:
        rx["K.o.-Verdacht"] = re.compile(r"\b(?:" + "|".join(map(re.escape, ko_woerter)) + ")", re.I)
    found = []
    for name, r in rx.items():
        words = sorted({m.group(0).lower() for m in r.finditer(text)})
        if words:
            found.append(f"{name} ({', '.join(words[:3])})")
    return "; ".join(found) or "keine"


def profil_block(p: dict[str, Any]) -> str:
    return "\n".join([
        f"Name: {p['name']}",
        f"Sucht: {p.get('ziel', '')}",
        f"Heute: {p['current_role']}",
        f"Kurz: {p['bio_short']}",
        f"Kernthemen: {', '.join(p['themen_kern'])}",
        f"Nahe Themen: {', '.join(p.get('themen_nah', []))}",
        f"Tabu: {', '.join(p.get('themen_tabu', []))}",
        f"Qualifikationen: {'; '.join(p['qualifikationen'])}",
        f"Fehlt: {', '.join(p.get('qualifikationen_fehlen', []))}",
        f"Sprachen: {', '.join(l['code'] + ' ' + l['level'] for l in p['languages'])}",
        f"Ort: {p['current_location']}",
        f"Nur online/remote: {'ja' if p.get('nur_online') else 'nein'}",
        f"Status: {p['status_rechtlich']}",
    ])


def score_job(job: dict[str, Any], p: dict[str, Any], client) -> dict[str, Any] | None:
    weights = {k: v for k, v in p["scorer_weights"].items() if not k.startswith("_")}
    prompt = PROMPT.format(
        vorname=p["name"].split()[0],
        profil=profil_block(p),
        gewichte="\n".join(f"  {k}: max {v}" for k, v in weights.items()),
        regeln=p.get("scoring_notes", "(keine)"),
        breakdown_keys=", ".join(f'"{k}": 0' for k in weights),
        titel=job.get("title", ""),
        firma=job.get("company", ""),
        ort=job.get("location", ""),
        remote="ja" if job.get("is_remote") else "unbekannt",
        quelle=job.get("source_board", ""),
        hinweise=hinweise(f"{job.get('title', '')}\n{job.get('description', '')}", p.get("ko_woerter", [])),
        text=(job.get("description") or "")[:3500],
    )
    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=700,
        )
        result = json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"    ⚠️  Bewertung fehlgeschlagen fuer '{job.get('title', '')[:50]}': {e}")
        return None

    try:
        result["breakdown"], result["score"] = apply_caps(result["breakdown"], weights)
    except (KeyError, TypeError, ValueError, AttributeError):
        result["score"] = int(result.get("score", 0) or 0)
    return result


def apply_caps(breakdown: dict[str, Any], weights: dict[str, int]) -> tuple[dict[str, int], int]:
    """Kleine Modelle rechnen schlecht (Test: Dimensionen 100, "score" 65). Deshalb zaehlt die Summe
    der gedeckelten Dimensionen, und eine 0 in einer K.o.-Dimension drueckt den Score hart nach unten."""
    bd = {k: min(int(breakdown.get(k, 0)), w) for k, w in weights.items()}
    score = sum(bd.values())
    if bd.get("qualifikation_fit", 1) == 0:
        score = min(score, 39)  # Pflicht-Qualifikation fehlt
    if bd.get("ort_fit", 1) == 0:
        score = min(score, 34)  # Praesenzpflicht an einem Ort, der nicht geht
    if bd.get("sprache_markt", 1) == 0:
        score = min(score, 40)  # Arbeitssprache, die die Person nicht spricht
    if bd.get("arbeitsmodell_fit", 1) == 0:
        score = min(score, 44)  # Arbeitsmodell nicht gewuenscht: unter MIN_SCORE 45, erscheint nicht im Radar
    return bd, score


def selftest() -> None:
    w = {"thema_fit": 30, "qualifikation_fit": 25, "ort_fit": 20, "arbeitsmodell_fit": 15, "sprache_markt": 10}
    assert apply_caps({"thema_fit": 99, "qualifikation_fit": "25", "ort_fit": 20, "arbeitsmodell_fit": 15, "sprache_markt": 10}, w)[1] == 100
    assert apply_caps({"thema_fit": 30, "qualifikation_fit": 0, "ort_fit": 20, "arbeitsmodell_fit": 15, "sprache_markt": 10}, w)[1] == 39
    assert apply_caps({"thema_fit": 30, "qualifikation_fit": 25, "ort_fit": 0, "arbeitsmodell_fit": 15, "sprache_markt": 10}, w)[1] == 34
    assert apply_caps({"thema_fit": 30, "qualifikation_fit": 10, "ort_fit": 20, "arbeitsmodell_fit": 15, "sprache_markt": 0}, w)[1] == 40
    assert apply_caps({"thema_fit": 30, "qualifikation_fit": 10, "ort_fit": 20, "arbeitsmodell_fit": 0, "sprache_markt": 10}, w)[1] == 44
    assert hinweise("Projekte ortsunabhängig über eine Videoplattform, freiberuflich") == "Online (ortsunabhängig, videoplattform); Freiberuflich (freiberuflich)"
    assert hinweise("Bewerben Sie sich online") == "keine"
    assert hinweise("Führerschein Klasse B erforderlich", ["Führerschein"]) == "K.o.-Verdacht (führerschein)"
    assert all(ist_sozial(u) for u in ["https://www.instagram.com/p/x", "https://www.linkedin.com/posts/x", "https://www.linkedin.com/in/x"])
    assert not any(ist_sozial(u) for u in ["https://www.linkedin.com/jobs/view/1", "https://example.com/stelle"])  # LinkedIn-Stellen bleiben
    print("selftest ok")


def main() -> int:
    from openai import OpenAI

    filtered = DATA / "filtered" / f"jobs_filtered_{TODAY}.json"
    jobs_path = filtered if filtered.exists() else DATA / "raw" / f"jobs_{TODAY}.json"
    if not jobs_path.exists():
        sys.exit(f"❌ {jobs_path} fehlt, erst Crawler ausfuehren.")

    jobs = json.loads(jobs_path.read_text())
    profile = json.loads(PROFILE_PATH.read_text())
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    seen = set(json.loads(SEEN_PATH.read_text())) if SEEN_PATH.exists() else set()
    out_path = RUNS_DIR / f"scored_{TODAY}.json"
    # Ein abgebrochener Lauf macht dort weiter, wo er war: was schon in dieser Datei steht, wird nicht noch einmal bewertet.
    # Alles von diesem Tag neu bewerten (z.B. nach geaenderten scoring_notes): die Datei loeschen.
    scored: list[dict[str, Any]] = json.loads(out_path.read_text()) if out_path.exists() else []
    fertig = {s["url"] for s in scored}
    print(f"=== Scorer {TODAY}: {len(jobs)} Treffer, davon {sum(j['url'] in fertig for j in jobs)} schon bewertet · LLM {LLM_MODEL} ===")

    for i, job in enumerate(jobs, 1):
        if job["url"] in fertig:
            continue
        if ist_sozial(job["url"]):
            seen.add(job["url"])  # nicht bewerten, aber merken, damit die Suche den Link nicht wieder bringt
            continue
        print(f"  [{i}/{len(jobs)}] {job.get('company', '')}: {job.get('title', '')[:60]}")
        result = score_job(job, profile, client)
        if result is None:
            continue  # nicht als gesehen markieren -> naechster Lauf versucht es erneut
        scored.append({**job, **result})
        seen.add(job["url"])
        save_json(out_path, scored, indent=2)  # nach jedem Treffer sichern, sonst ist bei einem Abbruch alles weg
        save_json(SEEN_PATH, sorted(seen), indent=1)
        time.sleep(0.2)

    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    save_json(out_path, scored, indent=2)
    save_json(SEEN_PATH, sorted(seen), indent=1)
    print(f"\n✅ {len(scored)} bewertet → {out_path.name} · Top-Scores: {[s.get('score') for s in scored[:5]]}")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.exit(main())
