# Anleitung für Claude Code

Dieses Repo ist der **Chancen-Radar**: ein wöchentlicher Such-Agent für Jobs, Aufträge und Kooperationen
(Suche über LinkedIn, Indeed und Firecrawl, Bewertung und Nachrichten über eine lokale KI mit Ollama,
Ergebnis als Übersichtsseite). Die Person vor dir programmiert wahrscheinlich nicht.
Übernimm die Technik und erkläre einfach.

## Grundregeln

- Antworte in der Sprache der Person (Standard: Deutsch, du-Form).
- Ein Schritt nach dem anderen. Erst weiter, wenn der vorige klappt.
- Befehle selbst ausführen. Die Person tut nur, was nur sie kann: Konto anlegen, App installieren, Datei auswählen, Fragen beantworten.
- `python3 scripts/doctor.py` ist die Wahrheit über den Stand. Rote Punkte zuerst beheben.
- Persönliches bleibt lokal: `data/` (außer `profile.example.json`), `.env` und `docs/index.html` nie committen. Schlüssel nie im Chat anzeigen.
- Nichts erfinden: Ins Profil kommt nur, was die Person sagt oder was im Lebenslauf steht.

## „Richte meinen Radar ein"

### Teil 1: Kennenlernen

1. Frag zuerst nach dem Lebenslauf (PDF, Word oder LinkedIn-Profil als PDF). Lies ihn und leg eine Kopie als `data/lebenslauf.<endung>` ab.
2. Geh [FRAGEBOGEN.md](FRAGEBOGEN.md) Block für Block durch, höchstens drei Fragen auf einmal. Was der Lebenslauf schon beantwortet, zeigst du als Vorschlag und lässt es bestätigen.
3. Schreib die Antworten mit nach `data/meine-antworten.md`. Liegt diese Datei schon ausgefüllt vor, nimm sie und frag nur nach, was fehlt.

### Teil 2: Profil bauen

Schreib `data/profile.json` nach dem Muster `data/profile.example.json`. Welche Antwort wohin gehört:

| Fragebogen | Felder im Profil |
|---|---|
| 1 Zweck | `ziel` |
| 2 Wer du bist | `name`, `current_role`, `bio_short` (2 Sätze), `bio_long` (5 bis 8 Sätze) |
| 3 Lebenslauf | `stations`, `belege`, `qualifikationen` |
| 4 Themen | `themen_kern`, `themen_nah`, `themen_tabu` |
| 5 Rahmen | `current_location`, `nur_online`, `status_rechtlich`, Regeln in `scoring_notes` |
| 6 Sprachen | `languages`, Regel für `sprache_markt` in `scoring_notes` |
| 7 Grenzen | `qualifikationen_fehlen`, `ko_woerter`, `ausschluss_woerter`, `avoid_companies`, Regeln in `scoring_notes` |
| 8 Nachrichten | `contact_line`, `schreib_regeln` |
| 9 Dein Radar | `display`, Zeitplan, Handy-Nachricht, Ideen für `search_terms` |

So füllst du die schwierigen Felder:

- **`scorer_weights`**: Die fünf Namen bleiben genau so (`thema_fit`, `qualifikation_fit`, `ort_fit`, `arbeitsmodell_fit`, `sprache_markt`), nur die Zahlen ändern, Summe 100. Eine 0 in den letzten vier drückt den Score hart nach unten (`apply_caps` in `src/03_scorer.py`).
- **`scoring_notes`**: harte, prüfbare Regeln pro Dimension, Muster: `ort_fit: voll bei remote; Präsenzpflicht außerhalb von Wien: 0.` Am Ende immer: `recommendation 'jetzt_angehen' nur bei score ab 80.`
- **`ko_woerter`**: Wörter für Pflicht-Anforderungen, die die Person nicht erfüllt (z.B. `Approbation`, `Führerschein`, `C1`). Der Bewerter bekommt sie als „K.o.-Verdacht" markiert.
- **`ausschluss_woerter`**: Treffer mit diesen Wörtern im Titel oder Text fliegen schon bei der Suche raus (z.B. `praktikum`, `werkstudent`). Sparsam, ganze Wörter.
- **`search_terms.jobspy`**: 5 bis 10 Einträge. `term` kurz wie ein Jobtitel (2 bis 4 Wörter, gern deutsch und englisch). `location` für LinkedIn auf Englisch (`Germany`, `Cologne, Germany`, `Austria`, `Switzerland`). `country_indeed` klein (`germany`, `austria`, `switzerland`, `uk`, `usa`). `"is_remote": true` grenzt die Suche auf Remote ein (LinkedIn ist dabei ungenau, die echte Prüfung machen Online-Filter und Bewerter). Optional `"sites": ["linkedin"]`. Jeder Eintrag kostet Laufzeit, mehr als 10 machen den Lauf sehr lang.
- **`search_terms.firecrawl_search`**: 6 bis 10 Suchen in natürlicher Sprache, je mit `kategorie`. Ein Portal gezielt durchsuchen: `site:freelancermap.de Projektmanagement remote`. Ideen in [QUELLEN.md](QUELLEN.md).
- **`kategorie`**: eine von `plattform`, `ausschreibung`, `kooperation`, `lehre`, `netzwerk`, `sichtbarkeit`, `nische` (Bedeutung in QUELLEN.md).

Zeig danach eine Zusammenfassung in fünf Zeilen (Ziel, Kernthemen, K.o.-Kriterien, Orte, Anzahl Suchbegriffe), hol eine Bestätigung und speichere erst dann.

### Teil 3: Installation

1. Voraussetzungen prüfen: `python3 --version` (3.10 oder neuer) und `ollama --version`. Fehlt Ollama: Person lädt es von https://ollama.com/download, installiert es und öffnet die App einmal.
2. `./scripts/install.sh` ausführen (Python-Umgebung, Pakete, KI-Modell, Zeitplan montags 06:00, Doctor).
3. Firecrawl (optional, empfohlen): Person legt auf https://www.firecrawl.dev ein kostenloses Konto an (Sign up), öffnet https://www.firecrawl.dev/app/api-keys und kopiert den Schlüssel (`fc-...`). Du trägst ihn in `.env` als `FIRECRAWL_API_KEY=` ein, ohne ihn anzuzeigen.
4. Handy-Nachricht (optional): mit der Person [docs/NTFY-Anleitung.md](docs/NTFY-Anleitung.md) durchgehen.
5. `python3 scripts/doctor.py` bis alles Kritische grün ist.
6. Erster Lauf: `./scripts/run_daily.sh` (10 bis 60 Minuten). Danach Doppelklick auf `Radar oeffnen.command`, oder `cd docs && python3 -m http.server 8899` und http://localhost:8899 öffnen.
7. Mit der Person die ersten Treffer anschauen und fragen: Was passt nicht? Daraus Regeln, Suchbegriffe und Wörter nachschärfen.

## Häufige Wünsche

| Wunsch | Wo |
|---|---|
| andere oder mehr Treffer | `search_terms` in `data/profile.json` |
| zu viele unpassende Treffer | `scoring_notes` schärfen, `ko_woerter`, `ausschluss_woerter` |
| nur remote | `"nur_online": true` (dann filtert `src/01b_remote_filter.py`) |
| Passung strenger oder lockerer | `scorer_weights`, `scoring_notes`, harte Deckel in `apply_caps` (`src/03_scorer.py`) |
| Nachrichten klingen fremd | `schreib_regeln`; ab welcher Passung geschrieben wird: `LETTER_MIN_SCORE` in `.env` (Standard 70) |
| eigene Farben | ganz oben im CSS von `src/05_dashboard_build.py` unter `:root` (`--bg`, `--acc` und die passenden `*-rgb` Werte) |
| anderer Tag oder Uhrzeit | `Weekday`/`Hour` in `scripts/install.sh`, dann das Skript erneut ausführen |
| bessere Texte | `LLM_MODEL=qwen2.5:14b` in `.env` plus `ollama pull qwen2.5:14b`, oder ein Cloud-Modell (siehe `.env.example`) |
| weitere Jobbörsen | `JOBSPY_SITES` in `.env` oder `"sites"` pro Eintrag, Liste in QUELLEN.md |
| eigene Hinweise unten auf der Seite | `data/notes.html` (einfaches HTML, erscheint unter den Funden) |
| online mit Passwort | Vercel: `vercel link`, dann `vercel env add RADAR_PASSWORD production`, dann `vercel deploy --prod`. Ab dann deployt jeder Lauf automatisch. Ohne gesetztes Passwort sperrt `middleware.js` alles. |

## Gute Anschreiben auf Zuruf

Die lokale KI (7B-Modell) liefert nur erste Entwürfe. Wenn die Person sagt „Schreib mir gute Anschreiben":
Lies `data/runs/latest.json` (oder die neueste `final_*.json`), nimm die besten Chancen ab 70 Punkten, öffne die Originalseite,
und schreib mit `data/profile.json`, `data/meine-antworten.md` und dem Lebenslauf ein Anschreiben in ihrer Stimme
(`schreib_regeln` beachten, nichts erfinden). Zeig es im Chat. Auf Wunsch in den Eintrag unter `application` (`betreff`, `nachricht`)
schreiben und `python3 src/05_dashboard_build.py` ausführen, dann steht es auf der Seite.

## Handrecherche eintragen

Wenn die Person Chancen von Hand recherchiert haben möchte: Recherchiere mit der Websuche, öffne jede Seite und prüfe sie wirklich. Schreib die Funde nach `data/runs/final_<YYYY-MM-DD>_hand.json` (der Wochenlauf überschreibt diese Datei nicht), eine Liste von Einträgen:

```json
{"url": "...", "title": "...", "company": "...", "bucket": "plattform",
 "score": 82, "was_ist_das": "...", "reasoning": "...", "anforderungen": ["..."], "concerns": ["..."],
 "naechster_schritt": "...", "kontakt": "...", "beleg": "wörtliches Zitat von der Seite",
 "geprueft_am": "YYYY-MM-DD", "arbeitsmodell": "freiberuflich", "ortsunabhaengig": "ja",
 "application": {"betreff": "...", "nachricht": "..."}}
```

Danach `python3 src/05_dashboard_build.py`. Einträge mit `geprueft_am` zeigt der Radar als geprüft. Wichtig: Funde, die älter als 35 Tage sind, fallen aus dem Radar.

## Technik in Kürze

- Ablauf: `01_crawler` → `01b_remote_filter` → `03_scorer` → `04_letter_writer` → `05_dashboard_build` → `06_notify`, gesteuert von `scripts/run_daily.sh` (mit 4-Stunden-Grenze für die Suche).
- KI: OpenAI-kompatible Schnittstelle, Standard Ollama unter `http://localhost:11434/v1` mit `qwen2.5:7b`, einstellbar in `.env`.
- Firecrawl: `firecrawl-py` ab Version 4 (`Firecrawl(timeout=120).search()` und `.scrape()`).
- Bewertete Links stehen in `data/seen_urls.json` und werden nicht erneut bezahlt oder bewertet.
- Der Scorer sichert nach jedem Treffer `data/runs/scored_<Datum>.json` und `seen_urls.json`. Nach einem Abbruch einfach noch einmal starten (`./scripts/run_daily.sh` oder `python3 src/03_scorer.py`), schon Bewertetes wird übersprungen. Alles von einem Tag neu bewerten (z.B. nach geänderten `scoring_notes`): diese `scored_<Datum>.json` löschen. Einen anderen Tag nachholen: `RUN_DATE=JJJJ-MM-TT` vor den Aufruf von `03_scorer.py` und `04_letter_writer.py`.
- Beiträge und Profile aus sozialen Netzen (Liste `SOZIAL` in `src/03_scorer.py`) werden nicht bewertet, PDFs liest der Crawler nicht ganz (Firecrawl rechnet sie pro Seite ab).
- `run_daily.sh` prüft vor der Suche, ob `LLM_MODEL` in Ollama liegt, und lädt es sonst neu. `caffeinate` hält den Mac während des Laufs wach.
- Selbsttests: `python3 src/01b_remote_filter.py --selftest`, `python3 src/03_scorer.py --selftest`, `python3 src/04_letter_writer.py --selftest`.
- Gebaut für macOS (launchd, `.command`-Dateien). Auf Windows oder Linux: Python-Teil läuft, Zeitplan und Starter musst du anpassen.
