# Handy-Nachricht bei neuen Chancen (ntfy)

Du bekommst eine Nachricht aufs Handy, wenn der Radar neue Chancen gefunden hat. Kostenlos, ohne Konto.

Dein Kanal hat einen geheimen Namen. Er steht in der Datei `.env` hinter `NTFY_TOPIC=`
(sieht aus wie `chancen-radar-a1b2c3`). Den brauchst du gleich.

## Auf dem Handy

1. Öffne den **App Store** (iPhone) oder **Play Store** (Android).
2. Suche nach **ntfy** (Entwickler: Philipp Heckel).
3. Tippe auf **Laden** bzw. **Installieren**, dann auf **Öffnen**.
4. Tippe in der App auf **+** (unten rechts, „Subscribe to topic“).
5. Gib bei **Topic name** den Namen genau so ein wie in `.env`. Server bleibt `ntfy.sh`.
6. Tippe auf **Subscribe**.

Fertig. Nach jedem Lauf mit neuen Funden kommt eine Nachricht mit der besten Passung.

## Testen

Im Projektordner auf dem Mac:

```bash
source .venv/bin/activate
python src/06_notify.py
```

Voraussetzung: Es gab schon einen Lauf (Doppelklick auf **Chancen suchen.command**).

## Gut zu wissen

- Der Kanalname ist das einzige Passwort. Behalte ihn für dich.
- Keine Nachricht? Prüfe: Mitteilungen für ntfy erlaubt, Name exakt gleich, Lauf hatte neue Funde.
