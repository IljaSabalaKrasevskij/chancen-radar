#!/usr/bin/env bash
# install.sh: einmalige Einrichtung (macOS). Ollama + Modell, Python-venv, .env,
# Launcher ausfuehrbar, woechentlicher Lauf (launchd), dann Doctor-Check. Mehrfach ausfuehrbar.

set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Chancen-Radar · Installation ==="

# 1) .env aus Vorlage (mit zufaelligem ntfy-Topic), zuerst, damit LLM_MODEL bekannt ist
if [ ! -f ".env" ]; then
  echo "→ .env aus Template"
  cp .env.example .env
  TOPIC="chancen-radar-$(openssl rand -hex 6)"
  sed -i.bak "s|NTFY_TOPIC=chancen-radar-CHANGE-ME-RANDOM|NTFY_TOPIC=$TOPIC|" .env && rm -f .env.bak
  echo "   ntfy topic: $TOPIC  (merken fuer die Handy-App, siehe docs/NTFY-Anleitung.md)"
fi
LLM_MODEL=$(grep -E '^LLM_MODEL=' .env | cut -d= -f2 | tr -d ' ')
LLM_MODEL=${LLM_MODEL:-qwen2.5:7b}

# 2) Ollama (lokales KI-Modell)
echo "→ Ollama pruefen"
if command -v ollama >/dev/null 2>&1; then
  echo "   Ollama gefunden. Modell ziehen: $LLM_MODEL (kann beim ersten Mal einige GB laden)"
  ollama pull "$LLM_MODEL" || echo "   ⚠️  'ollama pull' fehlgeschlagen. Laeuft Ollama? (App starten oder 'ollama serve')"
elif command -v brew >/dev/null 2>&1; then
  echo "   Ollama nicht da, via Homebrew installieren ..."
  brew install ollama && ollama pull "$LLM_MODEL" || echo "   ⚠️  bitte manuell: https://ollama.com/download, dann 'ollama pull $LLM_MODEL'"
else
  echo "   ⚠️  Ollama fehlt. Installieren: https://ollama.com/download  →  danach 'ollama pull $LLM_MODEL'"
fi

# 3) Python venv + Requirements
[ -d ".venv" ] || { echo "→ Python venv anlegen"; python3 -m venv .venv; }
source .venv/bin/activate
echo "→ Python-Pakete installieren"
pip install --upgrade pip wheel >/dev/null
pip install -r requirements.txt

# 4) Launcher + Skripte ausfuehrbar machen
chmod +x "$ROOT"/*.command "$ROOT"/scripts/*.sh 2>/dev/null || true

# 5) launchd (montags 06:00) fuer automatische Laeufe. Anderer Tag/Uhrzeit: Weekday/Hour unten aendern, Skript erneut starten.
LABEL="com.chancen-radar"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
echo "→ Woechentlicher Lauf nach $PLIST (montags 06:00)"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>${ROOT}/scripts/run_daily.sh</string></array>
  <key>StartCalendarInterval</key>
  <array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>6</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>${PATH}</string></dict>
  <key>StandardOutPath</key><string>${ROOT}/logs/launchd.out.log</string>
  <key>StandardErrorPath</key><string>${ROOT}/logs/launchd.err.log</string>
</dict></plist>
EOF
mkdir -p "$ROOT/logs"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST" 2>/dev/null || true

# 6) Doctor-Check
echo ""
echo "→ Setup-Check (Doctor)"
python3 scripts/doctor.py || true

echo ""
echo "=== Fertig. Naechste Schritte ==="
echo "1. Profil: in Claude Code sagen 'Richte meinen Radar ein' (FRAGEBOGEN.md)"
echo "2. Optional: Firecrawl-Schluessel in .env eintragen (Websuche), siehe README.md"
echo "3. Optional: Handy-Nachricht einrichten: docs/NTFY-Anleitung.md"
echo "4. Erster Lauf: Doppelklick 'Chancen suchen.command'  (oder ./scripts/run_daily.sh)"
