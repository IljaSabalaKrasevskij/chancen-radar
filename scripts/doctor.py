#!/usr/bin/env python3
"""
doctor.py: Setup-Checker. Prueft, ob alles fuer einen Lauf bereit ist.

Aufruf:  python3 scripts/doctor.py
Exit 0 = alle KRITISCHEN Checks gruen. Warnungen (gelb) sind optional.

Claude Code liest CLAUDE.md und ruft dieses Skript, um den Setup-Status zu pruefen
und den Nutzer gezielt durch fehlende Schritte zu fuehren.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# .env laden (ohne dotenv-Abhaengigkeit, damit der Doctor auch vor pip-install laeuft)
ENV = {}
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            ENV[k.strip()] = v.strip()

LLM_BASE_URL = ENV.get("LLM_BASE_URL", os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"))
LLM_MODEL = ENV.get("LLM_MODEL", os.environ.get("LLM_MODEL", "qwen2.5:7b"))
OLLAMA_ROOT = LLM_BASE_URL.rsplit("/v1", 1)[0]  # http://localhost:11434

crit_fail = 0
warns = 0


def ok(msg):
    print(f"  \033[32m✅ {msg}\033[0m")


def warn(msg):
    global warns
    warns += 1
    print(f"  \033[33m⚠️  {msg}\033[0m")


def fail(msg):
    global crit_fail
    crit_fail += 1
    print(f"  \033[31m❌ {msg}\033[0m")


def http_json(url, timeout=5, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


print("\n=== Chancen-Radar · Setup-Doctor ===\n")

# 1) Python-Version
print("Python & Pakete")
if sys.version_info >= (3, 10):
    ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")
else:
    fail(f"Python {sys.version_info.major}.{sys.version_info.minor}, brauche 3.10+")

# 2) Pflicht-Pakete
for pkg, hint in [("openai", "pip install -r requirements.txt"),
                  ("dotenv", "python-dotenv"),
                  ("requests", "requests")]:
    try:
        __import__(pkg)
        ok(f"Paket '{pkg}'")
    except ImportError:
        fail(f"Paket '{pkg}' fehlt: {hint}")
# jobspy + firecrawl sind nice-to-have (Crawler degradiert sonst)
for pkg in ["jobspy", "firecrawl"]:
    try:
        __import__(pkg)
        ok(f"Paket '{pkg}'")
    except ImportError:
        warn(f"Paket '{pkg}' fehlt, diese Suchquelle faellt weg (nicht kritisch)")

# 3) Ollama laeuft + Modell da (nur wenn die KI lokal laeuft; Cloud-Modell siehe .env.example)
LOKAL = "localhost" in LLM_BASE_URL or "127.0.0.1" in LLM_BASE_URL
print("\nKI-Modell")
if not LOKAL:
    ok(f"Cloud-Modell eingestellt ({LLM_MODEL} ueber {LLM_BASE_URL}), Ollama wird nicht gebraucht")
else:
    try:
        tags = http_json(f"{OLLAMA_ROOT}/api/tags", timeout=4)
        models = [m.get("name", "") for m in tags.get("models", [])]
        ok(f"Ollama laeuft ({OLLAMA_ROOT})")
        if any(m == LLM_MODEL or m.startswith(LLM_MODEL.split(':')[0]) for m in models):
            ok(f"Modell '{LLM_MODEL}' vorhanden")
        else:
            fail(f"Modell '{LLM_MODEL}' fehlt: 'ollama pull {LLM_MODEL}'  (vorhanden: {', '.join(models) or 'keine'})")
    except Exception as e:
        fail(f"Ollama nicht erreichbar unter {OLLAMA_ROOT}: installieren (ollama.com) und App starten. ({e})")

# 4) Echter Mini-LLM-Ping (nur lokal und wenn Ollama oben ok)
if LOKAL and crit_fail == 0:
    try:
        body = json.dumps({
            "model": LLM_MODEL,
            "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
            "stream": False,
            "options": {"num_predict": 5},
        }).encode()
        r = http_json(f"{OLLAMA_ROOT}/api/chat", timeout=60, data=body,
                      headers={"Content-Type": "application/json"})
        reply = (r.get("message", {}) or {}).get("content", "").strip()
        ok(f"LLM antwortet ('{reply[:20]}')")
    except Exception as e:
        warn(f"LLM-Ping fehlgeschlagen (Modell laedt evtl. noch): {e}")

# 5) .env + Keys
print("\nKonfiguration")
if env_file.exists():
    ok(".env vorhanden")
else:
    fail(".env fehlt: './scripts/install.sh' erzeugt sie aus .env.example")
if ENV.get("FIRECRAWL_API_KEY", "").startswith("fc-"):
    ok("FIRECRAWL_API_KEY gesetzt")
else:
    warn("FIRECRAWL_API_KEY fehlt, die Websuche (Plattformen, Kooperationen) faellt weg. LinkedIn/Indeed laufen trotzdem. Key: firecrawl.dev")
topic = ENV.get("NTFY_TOPIC", "")
if topic and "CHANGE-ME" not in topic:
    ok(f"NTFY_TOPIC gesetzt ({topic})")
else:
    warn("NTFY_TOPIC nicht gesetzt, keine Handy-Nachricht (optional, siehe docs/NTFY-Anleitung.md)")

# 6) Profil + CV
print("\nProfil")
prof = ROOT / "data" / ENV.get("PROFILE_FILE", "profile.json")
if prof.exists():
    try:
        p = json.loads(prof.read_text())
        need = ["name", "ziel", "themen_kern", "qualifikationen", "scorer_weights", "search_terms", "display"]
        miss = [k for k in need if k not in p]
        if miss:
            fail(f"profile.json unvollstaendig, es fehlt: {miss}")
        elif p.get("name") == "Vorname Nachname":
            fail("profile.json ist noch das Beispiel. In Claude Code sagen: 'Richte meinen Radar ein' (FRAGEBOGEN.md)")
        else:
            ok(f"profile.json ok ({p.get('name')})")
    except Exception as e:
        fail(f"profile.json nicht lesbar: {e}")
else:
    fail(f"{prof.name} fehlt. In Claude Code sagen: 'Richte meinen Radar ein', Claude stellt die Fragen aus FRAGEBOGEN.md")

# Verdict
print("\n" + "=" * 40)
if crit_fail == 0:
    print(f"\033[32m✅ BEREIT für einen Lauf.\033[0m  ({warns} Warnung(en))")
    print("Naechster Schritt:  ./scripts/run_daily.sh   oder Doppelklick auf 'Chancen suchen.command'")
    sys.exit(0)
else:
    print(f"\033[31m❌ {crit_fail} kritische(r) Punkt(e) offen.\033[0m Bitte oben rot markierte beheben.")
    sys.exit(1)
