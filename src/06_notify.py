#!/usr/bin/env python3
"""
06_notify.py: Handy-Nachricht via ntfy.sh.

Liest data/runs/latest.json, formatiert ein Summary,
sendet POST an https://ntfy.sh/<NTFY_TOPIC>.

Auf dem Handy abonniert man das Topic in der ntfy-App (Anleitung: docs/NTFY-Anleitung.md).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

RUNS_DIR = ROOT / "data" / "runs"
TODAY = datetime.now().strftime("%Y-%m-%d")

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "")
APP_NAME = os.environ.get("APP_NAME", "Chancen-Radar")


def build_message(jobs: list[dict]) -> tuple[str, str, str]:
    """Returns (title, body, priority)."""
    jobs = [j for j in jobs if j.get("score", 0) >= 45]  # wie im Radar sichtbar
    if not jobs:
        return (APP_NAME, f"Diese Woche nichts Neues ({TODAY}). Der Radar zeigt weiter die letzten Funde.", "low")

    top = jobs[0]  # sortiert absteigend
    n_top = sum(1 for j in jobs if j.get("score", 0) >= 80)
    n_msgs = sum(1 for j in jobs if (j.get("application") or {}).get("nachricht"))

    title = f"{APP_NAME} · {len(jobs)} neue Chancen"
    body = (
        f"Beste Passung {top.get('score', 0)}/100: {(top.get('title') or '')[:60]} ({top.get('company') or ''})\n"
        f"{n_top} zum sofort Angehen · {n_msgs} Nachrichten vorbereitet"
    )
    priority = "high" if top.get("score", 0) >= 80 else "default"
    return (title, body, priority)


def main() -> int:
    if not NTFY_TOPIC or "CHANGE-ME" in NTFY_TOPIC:
        print("⚠️  NTFY_TOPIC nicht gesetzt, keine Handy-Nachricht")
        return 0

    latest = RUNS_DIR / "latest.json"
    if not latest.exists():
        print(f"⚠️  {latest} fehlt, keine Handy-Nachricht moeglich")
        return 0

    jobs = json.loads(latest.read_text())
    title, body, priority = build_message(jobs)

    print(f"=== ntfy.sh Push: {TODAY} ===")
    print(f"Title: {title}")
    print(f"Body: {body}")

    headers = {"Title": title, "Priority": priority, "Tags": "briefcase,sparkles"}
    if DASHBOARD_URL:
        headers["Click"] = DASHBOARD_URL
        headers["Actions"] = f"view, Radar oeffnen, {DASHBOARD_URL}, clear=true"

    try:
        resp = requests.post(
            f"{NTFY_SERVER.rstrip('/')}/{NTFY_TOPIC}",
            data=body.encode("utf-8"),
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        print(f"✅ Push sent (HTTP {resp.status_code})")
    except Exception as e:
        print(f"❌ Push failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
