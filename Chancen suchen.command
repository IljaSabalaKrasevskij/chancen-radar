#!/bin/bash
# Doppelklick: sucht jetzt neue Chancen, baut deinen Radar, oeffnet den Browser.
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null

echo "──────────────────────────────────────────────"
echo "  Suche neue Chancen ... (ein paar Minuten, KI laeuft lokal)"
echo "──────────────────────────────────────────────"
bash ./scripts/run_daily.sh
STATUS=$?
echo ""
if [ $STATUS -ne 0 ]; then
  echo "⚠️  Etwas ist schiefgelaufen. Tipp: 'python3 scripts/doctor.py' zeigt was fehlt."
  read -p "Enter zum Schliessen..."
  exit 1
fi

PORT=8899
echo "Fertig. Oeffne deinen Radar: http://localhost:$PORT"
echo "(Fenster offen lassen. Schliessen beendet die Anzeige.)"
( sleep 1; open "http://localhost:$PORT" ) &
cd docs && exec python3 -m http.server $PORT
