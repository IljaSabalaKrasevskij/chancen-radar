#!/bin/bash
# Doppelklick: oeffnet deinen Chancen-Radar im Browser (letzter Lauf).
cd "$(dirname "$0")"
if [ ! -f docs/index.html ]; then
  echo "Noch kein Radar vorhanden. Bitte zuerst 'Chancen suchen' doppelklicken."
  read -p "Enter zum Schliessen..."
  exit 1
fi
PORT=8899
echo "──────────────────────────────────────────────"
echo "  Radar: http://localhost:$PORT"
echo "  Dieses Fenster offen lassen. Schliessen beendet die Anzeige."
echo "──────────────────────────────────────────────"
( sleep 1; open "http://localhost:$PORT" ) &
cd docs && exec python3 -m http.server $PORT
