#!/usr/bin/env bash
# run_daily.sh: ein kompletter Lauf des Chancen-Radars (laeuft woechentlich, siehe install.sh).
#
#   1. 01_crawler.py         LinkedIn/Indeed (jobspy) + Firecrawl-Websuche
#   2. 01b_remote_filter.py  Online-Check (nur wenn im Profil "nur_online": true)
#   3. 03_scorer.py          Passung 0-100 auf Deutsch (Ollama lokal)
#   4. 04_letter_writer.py   Nachricht pro Top-Chance (Ollama lokal)
#   5. 05_dashboard_build.py Radar-Seite (docs/index.html)
#   6. 06_notify.py          Handy-Nachricht via ntfy (optional)
#   7. Vercel-Deploy         nur wenn ein Vercel-Projekt verknuepft ist (optional, mit Passwort)
#
# Laufzeit ca. 10-60 Min. Kosten: KI lokal gratis; Firecrawl je nach Suchbegriffen 30-150 Credits pro Lauf.

set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

[ -f .env ] && { set -a; source .env; set +a; }
[ -f .venv/bin/activate ] && source .venv/bin/activate
export PYTHONUNBUFFERED=1  # Fortschritt sofort im Log, nicht erst am Ende

DATE=$(date +%Y-%m-%d); STAMP=$(date +%H%M)
mkdir -p logs
LOGFILE="logs/run_${DATE}_${STAMP}.log"
echo "=== Run ${DATE} ${STAMP} ===" | tee -a "$LOGFILE"

OLLAMA_ROOT="${LLM_BASE_URL:-http://localhost:11434/v1}"; OLLAMA_ROOT="${OLLAMA_ROOT%/v1}"
if [[ "$OLLAMA_ROOT" == *localhost* || "$OLLAMA_ROOT" == *127.0.0.1* ]] && ! curl -sf "$OLLAMA_ROOT/api/tags" >/dev/null 2>&1; then
  echo "❌ Ollama nicht erreichbar ($OLLAMA_ROOT). Ollama-App starten (oder 'ollama serve'). Details: python3 scripts/doctor.py" | tee -a "$LOGFILE"
  exit 1
fi
[ -z "${FIRECRAWL_API_KEY:-}" ] && echo "⚠️  FIRECRAWL_API_KEY fehlt, Websuche wird uebersprungen (LinkedIn/Indeed laufen trotzdem)" | tee -a "$LOGFILE"

# ponytail: harte Obergrenze 4 Std. fuer die Suche (macOS hat keinen timeout-Befehl, perl schon).
# Ein haengender Netzwerk-Aufruf blockiert sonst still alle folgenden Wochenlaeufe.
perl -e 'alarm shift; exec @ARGV' 14400 python3 src/01_crawler.py 2>&1 | tee -a "$LOGFILE"
python3 src/01b_remote_filter.py  2>&1 | tee -a "$LOGFILE"
python3 src/03_scorer.py          2>&1 | tee -a "$LOGFILE"
python3 src/04_letter_writer.py   2>&1 | tee -a "$LOGFILE"
python3 src/05_dashboard_build.py 2>&1 | tee -a "$LOGFILE"
python3 src/06_notify.py          2>&1 | tee -a "$LOGFILE" || echo "   Handy-Nachricht uebersprungen" | tee -a "$LOGFILE"

# Optional online mit Passwort (README: "Radar online stellen"). Ohne verknuepftes Vercel-Projekt passiert nichts.
VERCEL_BIN="$(command -v vercel || true)"
if [ -f .vercel/project.json ] && [ -n "$VERCEL_BIN" ]; then
  "$VERCEL_BIN" deploy --prod --yes 2>&1 | grep -E "Aliased|Error" | tee -a "$LOGFILE" || echo "   Vercel-Deploy fehlgeschlagen" | tee -a "$LOGFILE"
fi

echo "=== DONE ${DATE} ${STAMP} ===" | tee -a "$LOGFILE"
echo "Ansehen: Doppelklick auf 'Radar oeffnen.command'"
