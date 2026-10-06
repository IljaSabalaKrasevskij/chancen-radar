#!/usr/bin/env python3
"""
05_dashboard_build.py: Der Chancen-Radar als eine ruhige, deutsche HTML-Seite.

Liest alle data/runs/final_*.json der letzten 35 Tage (neuester Stand gewinnt pro Link),
blendet Score < 45 aus und sortiert nach Passung. Von Hand recherchierte Funde liegen in
data/runs/final_YYYY-MM-DD_hand.json (gleiches Format, ueberschreibt der Wochenlauf nicht).
Farben: alles steht oben im CSS unter :root (--bg, --acc und die passenden *-rgb Werte).

Optional: data/notes.html wird als Hinweis-Block unter die Funde gesetzt (eigene Notizen, Links, Fragen).

Output: docs/index.html (lokal ansehen oder per Vercel mit Passwort online stellen)
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RUNS_DIR = DATA / "runs"
DOCS_DIR = ROOT / "docs"
PROFILE_PATH = DATA / os.environ.get("PROFILE_FILE", "profile.json")
WINDOW_DAYS = 35
MIN_SCORE = 45

MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]

# Reihenfolge = Reihenfolge im Filter. Unbekannte Kategorien landen unter "nische". Was hinter jeder steckt: QUELLEN.md
KAT_NAME = {
    "plattform": "Plattformen und Firmen",
    "ausschreibung": "Offene Ausschreibungen",
    "kooperation": "Kooperationen",
    "lehre": "Lehren und weitergeben",
    "netzwerk": "Deine Netzwerke",
    "sichtbarkeit": "Gefunden werden",
    "nische": "Kreative Nischen",
}


def esc(v: Any) -> str:
    return html.escape(str(v or ""))


def datum_de(d: datetime) -> str:
    return f"{d.day}. {MONATE[d.month - 1]} {d.year}"


def stufe(score: int) -> tuple[str, str]:
    if score >= 80:
        return "top", "Jetzt angehen"
    if score >= 60:
        return "mid", "Genauer anschauen"
    return "low", "Vielleicht später"


def load_items() -> tuple[list[dict[str, Any]], datetime, int, int]:
    """Neueste Bewertung pro Link aus den letzten WINDOW_DAYS Tagen."""
    files = sorted(RUNS_DIR.glob("final_*.json"))
    cutoff = datetime.now() - timedelta(days=WINDOW_DAYS)
    by_url: dict[str, dict[str, Any]] = {}
    newest = datetime.now()
    for f in files:
        run_day = datetime.strptime(f.stem.removeprefix("final_")[:10], "%Y-%m-%d")  # auch final_..._hand.json
        if run_day < cutoff:
            continue
        newest = run_day
        for item in json.loads(f.read_text()):
            by_url[item.get("url") or item.get("id")] = {**item, "_run": run_day}
    items = list(by_url.values())
    shown = [i for i in items if int(i.get("score") or 0) >= MIN_SCORE]
    for i in shown:
        i["_neu"] = len(files) > 1 and i["_run"] == newest
        b = i.get("bucket") or "ausschreibung"
        i["bucket"] = b if b in KAT_NAME else "nische"
    shown.sort(key=lambda i: int(i.get("score") or 0), reverse=True)
    return shown, newest, len(items), len(files)



TIERS = [
    ("A", "top", "Jetzt angehen", "Passung 80 bis 100. Hier lohnt sich diese Woche jede Minute."),
    ("B", "mid", "Genauer anschauen", "Passung 60 bis 79. Gute Türen, bei denen ein Detail noch zu klären ist."),
    ("C", "low", "Vielleicht später", "Passung 45 bis 59. Im Blick behalten, nicht jetzt."),
]


def chip(text: str, kind: str = "") -> str:
    return f'<span class="chip {kind}">{esc(text)}</span>' if text else ""


def online_chip(v: str) -> str:
    kind = {"ja": "ok", "wahrscheinlich": "ok", "nein": "no"}.get((v or "").lower(), "warn")
    return chip(f"Ortsunabhängig: {v or 'unklar'}", kind)


def as_list(v: Any) -> list[str]:
    if not v:
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


def initials(name: str) -> str:
    words = [w for w in (name or "?").replace("(", " ").split() if w[:1].isalnum()]
    return "".join(w[0] for w in words[:2]).upper() or "?"


def modell(i: dict[str, Any]) -> str:
    m = i.get("arbeitsmodell") or ""
    return m[:1].upper() + m[1:]


def render_card(i: dict[str, Any], uid: str) -> str:
    score = int(i.get("score") or 0)
    level, label = stufe(score)
    what = i.get("was_ist_das") or (i.get("description") or "")[:200]
    return f"""
<article class="card card-{level}" data-id="{esc(i.get('id') or uid)}" data-cat="{esc(i['bucket'])}" id="c-{uid}">
  <div class="card-head">
    <div class="score"><b>{score}</b><span>/100</span></div>
    <div class="status" role="group" aria-label="Status merken">
      <button type="button" data-st="fav" title="Merken" aria-label="Merken">★</button>
      <button type="button" data-st="done" title="Erledigt" aria-label="Erledigt">✓</button>
      <button type="button" data-st="skip" title="Ausblenden" aria-label="Ausblenden">✕</button>
    </div>
  </div>
  <span class="cat">{esc(KAT_NAME.get(i['bucket'], ''))}{'<em class="neu">neu</em>' if i.get('_neu') else ''}</span>
  <div class="org"><i>{esc(initials(i.get('company')))}</i><span>{esc(i.get('company'))}</span></div>
  <h3>{esc(i.get('title'))}</h3>
  <p class="what">{esc(what)}</p>
  <div class="chips">{chip(modell(i))}{online_chip(i.get('ortsunabhaengig'))}</div>
  <div class="card-foot">
    <span class="tier-label">{label}</span>
    <button type="button" class="open" data-open="{uid}">Details ansehen →</button>
  </div>
</article>"""


def render_drawer(i: dict[str, Any], uid: str) -> str:
    score = int(i.get("score") or 0)
    level, label = stufe(score)
    app = i.get("application") or {}

    def block(title: str, body: str) -> str:
        return f'<section class="d-sec"><h4>{title}</h4>{body}</section>' if body else ""

    def ul(v: Any) -> str:
        items = as_list(v)
        return f"<ul>{''.join(f'<li>{esc(x)}</li>' for x in items)}</ul>" if items else ""

    def p(v: Any) -> str:
        return f"<p>{esc(v)}</p>" if v else ""

    facts = [("Arbeitsform", modell(i)), ("Ortsunabhängig", i.get("ortsunabhaengig") or "unklar"),
             ("Bereich", KAT_NAME.get(i["bucket"], "")), ("Vergütung", i.get("salary"))]
    fact_html = "".join(f'<div><span>{k}</span><b>{esc(v)}</b></div>' for k, v in facts if v)
    beleg = ""
    if i.get("beleg"):
        when = f", geprüft am {esc(i['geprueft_am'])}" if i.get("geprueft_am") else ""
        beleg = f'<blockquote>„{esc(i["beleg"])}“<cite>Zitat von der Seite{when}</cite></blockquote>'
    msg = ""
    if app.get("nachricht"):
        head = "Vorschlag für deine Nachricht" if i.get("geprueft_am") else "Automatischer Entwurf, bitte gegenlesen"
        msg = (f'<section class="d-sec msg"><h4>{head}</h4>'
               f'<p class="subj">Betreff: {esc(app.get("betreff"))}</p>'
               f'<textarea id="msg-{uid}" readonly rows="10">{esc(app["nachricht"])}</textarea></section>')
    copy_btn = f'<button type="button" class="btn-light" data-copy="msg-{uid}">Nachricht kopieren</button>' if msg else ""
    return f"""
<template id="d-{uid}">
  <div class="d-head">
    <div class="d-score d-{level}"><b>{score}</b><span>/100</span><em>{label}</em></div>
    <div>
      <div class="org"><i>{esc(initials(i.get('company')))}</i><span>{esc(i.get('company'))}</span></div>
      <h2>{esc(i.get('title'))}</h2>
    </div>
  </div>
  <div class="facts">{fact_html}</div>
  {block('Worum es geht', p(i.get('was_ist_das')))}
  {block('Warum es zu dir passt', p(i.get('reasoning')))}
  {block('Was sie verlangen', ul(i.get('anforderungen')))}
  {block('Worauf du achten solltest', ul(i.get('concerns')))}
  {block('Dein nächster Schritt', p(i.get('naechster_schritt')))}
  {block('Kontakt', p(i.get('kontakt')))}
  {beleg}
  {msg}
  <div class="d-foot">
    <a class="btn-gold" href="{esc(i.get('url'))}" target="_blank" rel="noopener noreferrer">Zur Seite →</a>
    {copy_btn}
  </div>
</template>"""


CSS = """
:root{
  /* Farben anpassen: nur hier. Die *-rgb Werte muessen zur Hex-Farbe darueber passen. */
  --bg:#0B1B24; --bg-2:#10242F; --bg-3:#173343; --bg-rgb:11,27,36;
  --acc:#E3A64F; --acc-hi:#F2C27A; --acc-deep:#B0782E; --acc-rgb:227,166,79;
  --cream:#FBF6EC; --cream-2:#FFFCF6; --sky:#CFE3EA; --sky-rgb:207,227,234;
  --ink:#F4F1E6; --ink-2:#C1CCD2; --ink-3:#8D9CA5;
  --line:rgba(244,241,230,.12); --line-2:rgba(244,241,230,.24);
  --c-ink:#0B1B24; --c-ink-2:#45535C; --c-line:#E9DEC9;
  --ok:#1F6B47; --ok-bg:#DDF0E5; --warn:#7A5300; --warn-bg:#FBEBC8; --no:#962E2E; --no-bg:#F8E0E0;
  --sans:"Avenir Next","Figtree",system-ui,-apple-system,"Segoe UI",sans-serif;
  --hand:"Caveat","Bradley Hand",cursive;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink)}
body{font:16px/1.55 var(--sans);-webkit-font-smoothing:antialiased;min-height:100vh;
  background-image:radial-gradient(circle at 15% -10%,rgba(var(--acc-rgb),.16),transparent 45%),
    radial-gradient(circle at 90% 5%,rgba(var(--sky-rgb),.08),transparent 40%),
    radial-gradient(circle at 50% 110%,var(--bg-3),transparent 60%);background-attachment:fixed}
body.locked{overflow:hidden}
a{color:inherit}
button{font:inherit;cursor:pointer}
:focus-visible{outline:2px solid var(--acc-hi);outline-offset:3px;border-radius:6px}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px 80px}

/* Hero */
.hero{display:flex;gap:36px;align-items:center;padding:56px 0 40px;border-bottom:1px solid var(--line)}
.medal{flex:0 0 172px;height:172px;border-radius:50%;position:relative;display:grid;place-items:center;
  background:radial-gradient(circle at 35% 30%,var(--bg-3),var(--bg) 70%);
  box-shadow:0 0 0 1px rgba(var(--acc-rgb),.5),0 0 0 9px rgba(var(--acc-rgb),.07),0 0 60px rgba(var(--acc-rgb),.25),inset 0 0 30px rgba(0,0,0,.5)}
.medal::before{content:"";position:absolute;inset:12px;border-radius:50%;border:1px dashed rgba(var(--acc-rgb),.45)}
.medal b{font:700 84px/1 var(--sans);letter-spacing:-.04em;
  background:linear-gradient(160deg,var(--acc-hi),var(--acc) 50%,var(--acc-deep));-webkit-background-clip:text;background-clip:text;color:transparent}
.medal span{position:absolute;bottom:30px;font:500 22px/1 var(--hand);color:var(--acc-hi)}
@media (prefers-reduced-motion:no-preference){.medal{animation:glow 6s ease-in-out infinite}}
@keyframes glow{50%{box-shadow:0 0 0 1px rgba(var(--acc-rgb),.6),0 0 0 9px rgba(var(--acc-rgb),.1),0 0 90px rgba(var(--acc-rgb),.38),inset 0 0 30px rgba(0,0,0,.5)}}
.eyebrow{font-size:12px;letter-spacing:.3em;text-transform:uppercase;color:var(--acc);font-weight:600}
.hero h1{font:700 clamp(38px,6vw,64px)/1 var(--sans);letter-spacing:-.035em;margin:10px 0 10px}
.hero .sub{color:var(--ink-2);max-width:60ch;margin:0 0 22px;font-size:17px}
.stats{display:flex;flex-wrap:wrap;gap:12px}
.stat{border:1px solid var(--line-2);border-radius:14px;padding:10px 16px;background:rgba(255,255,255,.03);font-size:13px;color:var(--ink-2)}
.stat b{display:block;font-size:26px;line-height:1.1;color:var(--ink);font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.stat.gold b{color:var(--acc-hi)}

/* Guide */
.guide{margin-top:36px;border:1px solid rgba(var(--acc-rgb),.45);border-radius:20px;padding:26px 28px;
  background:linear-gradient(160deg,rgba(var(--acc-rgb),.08),rgba(255,255,255,.02))}
.guide-head{display:flex;justify-content:space-between;align-items:center;gap:12px}
.guide h2{margin:0;font-size:24px;letter-spacing:-.02em}
.ghost{background:transparent;border:1px solid var(--line-2);color:var(--ink-2);border-radius:99px;padding:7px 14px;font-size:14px;white-space:nowrap}
.guide ol{list-style:none;padding:0;margin:20px 0 0;display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:20px;counter-reset:s}
.guide li{counter-increment:s;font-size:15px;color:var(--ink-2)}
.guide li::before{content:counter(s);display:grid;place-items:center;width:34px;height:34px;border-radius:50%;margin-bottom:10px;
  background:linear-gradient(160deg,var(--acc-hi),var(--acc-deep));color:var(--bg);font-weight:700}
.guide li b{display:block;color:var(--ink);font-size:16px;margin-bottom:4px}
.guide.hidden ol{display:none}

/* Top 5 */
.top5{margin-top:40px}
.top5 h2,.tier h2{margin:0;font-size:26px;letter-spacing:-.02em}
.top5 ol{list-style:none;margin:16px 0 0;padding:0;display:grid;gap:10px;counter-reset:r}
.top5 li{counter-increment:r}
.top5 button{width:100%;display:grid;grid-template-columns:44px 1fr auto;gap:14px;align-items:center;text-align:left;color:var(--ink);
  background:rgba(255,255,255,.03);border:1px solid var(--line);border-radius:14px;padding:14px 18px;transition:border-color .2s,background .2s}
.top5 button:hover{border-color:var(--acc);background:rgba(var(--acc-rgb),.07)}
.top5 button::before{content:counter(r);font:700 22px var(--sans);color:var(--acc-hi)}
.top5 .t{font-weight:600}.top5 .o{display:block;font-size:14px;color:var(--ink-3)}
.top5 .s{font:700 22px var(--sans);color:var(--acc-hi);font-variant-numeric:tabular-nums}
.top5 .leer{color:var(--ink-2)}

/* Filter */
.filter{position:sticky;top:0;z-index:5;margin:44px -24px 0;padding:14px 24px;display:flex;gap:8px;flex-wrap:wrap;
  background:rgba(var(--bg-rgb),.86);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
.filter button{border:1px solid var(--line-2);background:transparent;color:var(--ink-2);border-radius:99px;padding:7px 14px;font-size:14px;white-space:nowrap}
.filter button[aria-pressed="true"]{background:var(--acc);border-color:var(--acc);color:var(--bg);font-weight:600}

/* Tier bands */
.tier{margin-top:44px}
.band{display:flex;align-items:center;gap:20px;padding:16px 22px;border-radius:16px;margin-bottom:18px;
  background:linear-gradient(90deg,rgba(var(--acc-rgb),.16),rgba(var(--acc-rgb),0) 70%);border-left:3px solid var(--acc)}
.band .L{font:700 46px/1 var(--sans);color:var(--acc-hi);letter-spacing:-.04em}
.band p{margin:2px 0 0;color:var(--ink-2);font-size:15px}
.band .n{margin-left:auto;border:1px solid var(--line-2);border-radius:99px;padding:5px 14px;font-size:14px;color:var(--ink-2);white-space:nowrap}
.tier-mid .band{border-left-color:var(--sky);background:linear-gradient(90deg,rgba(var(--sky-rgb),.12),transparent 70%)}
.tier-mid .band .L{color:var(--sky)}
.tier-low .band{border-left-color:var(--ink-3);background:linear-gradient(90deg,rgba(141,156,165,.1),transparent 70%)}
.tier-low .band .L{color:var(--ink-3)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(330px,100%),1fr));gap:18px}

/* Cards */
.card{position:relative;min-width:0;display:flex;flex-direction:column;gap:10px;padding:22px 22px 18px;border-radius:18px;color:var(--c-ink);
  background:linear-gradient(170deg,var(--cream-2),var(--cream));border:1px solid var(--c-line);
  box-shadow:0 1px 0 rgba(255,255,255,.6) inset,0 18px 40px -22px rgba(0,0,0,.7);transition:transform .25s,box-shadow .25s}
.card-head{display:flex;justify-content:space-between;align-items:flex-start}
.card-head .score b{font:700 44px/1 var(--sans);letter-spacing:-.04em}
.card-head .score span{font-size:14px;color:var(--c-ink-2);margin-left:2px}
article.card-top{box-shadow:0 0 0 1.5px var(--acc),0 22px 50px -20px rgba(var(--acc-rgb),.45)}
.card-top .score b{background:linear-gradient(160deg,var(--acc-deep),#7A4E12);-webkit-background-clip:text;background-clip:text;color:transparent}
@media (hover:hover){.card:hover{transform:translateY(-3px);box-shadow:0 0 0 1.5px var(--acc),0 26px 50px -22px rgba(0,0,0,.8)}}
.status{display:flex;gap:6px}
.status button{width:34px;height:34px;border-radius:10px;border:1px solid var(--c-line);background:#fff;color:var(--c-ink-2);font-size:15px;line-height:1}
.status button:hover{border-color:var(--c-ink)}
.card[data-state="fav"] [data-st="fav"]{background:var(--acc);border-color:var(--acc);color:var(--bg)}
.card[data-state="done"] [data-st="done"]{background:var(--ok);border-color:var(--ok);color:#fff}
.card[data-state="done"]{opacity:.55}
.card[data-state="skip"]{display:none}
.show-skipped .card[data-state="skip"]{display:flex;opacity:.4}
.cat{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#8A5A17;font-weight:600}
.neu{font-style:normal;margin-left:8px;background:var(--bg);color:var(--acc-hi);border-radius:99px;padding:2px 8px;letter-spacing:.08em}
.org{display:flex;align-items:center;gap:10px;font-size:14px;color:var(--c-ink-2);min-width:0}
.org i{flex:0 0 auto;display:grid;place-items:center;width:28px;height:28px;border-radius:8px;font-style:normal;font-size:11px;font-weight:700;
  background:var(--bg);color:var(--acc-hi)}
.org span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.card h3{margin:0;font-size:20px;line-height:1.25;letter-spacing:-.015em}
.what{margin:0;font-size:15px;color:var(--c-ink-2);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:13px;line-height:1;padding:6px 10px;border-radius:99px;background:#F2E9D8;color:var(--c-ink-2);white-space:nowrap}
.chip.ok{background:var(--ok-bg);color:var(--ok)}.chip.warn{background:var(--warn-bg);color:var(--warn)}.chip.no{background:var(--no-bg);color:var(--no)}
.card-foot{margin-top:auto;padding-top:12px;border-top:1px solid var(--c-line);display:flex;justify-content:space-between;align-items:center;gap:10px}
.tier-label{font-size:13px;color:var(--c-ink-2)}
.open{border:0;border-radius:99px;padding:10px 16px;font-weight:600;font-size:14px;color:var(--bg);
  background:linear-gradient(160deg,var(--acc-hi),var(--acc));box-shadow:0 6px 16px -8px rgba(var(--acc-rgb),.7)}
.card-low .open{background:var(--bg);color:var(--cream)}

/* Drawer */
.scrim{position:fixed;inset:0;background:rgba(0,0,0,.55);backdrop-filter:blur(3px);opacity:0;pointer-events:none;transition:opacity .3s;z-index:20}
.drawer{position:fixed;top:0;right:0;bottom:0;width:min(640px,100%);z-index:21;background:var(--bg-2);border-left:1px solid rgba(var(--acc-rgb),.35);
  transform:translateX(102%);transition:transform .38s cubic-bezier(.22,1,.36,1);display:flex;flex-direction:column}
.open-d .scrim{opacity:1;pointer-events:auto}.open-d .drawer{transform:none}
.d-bar{display:flex;justify-content:space-between;align-items:center;padding:16px 24px;border-bottom:1px solid var(--line);font-size:13px;color:var(--ink-3)}
.d-body{overflow-y:auto;padding:26px 28px 120px;display:grid;gap:22px}
.d-head{display:grid;grid-template-columns:auto 1fr;gap:20px;align-items:start}
.d-score b{font:700 56px/1 var(--sans);letter-spacing:-.04em;color:var(--acc-hi)}
.d-score span{color:var(--ink-3)}
.d-score em{display:block;font-style:normal;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--acc);margin-top:6px}
.d-mid b{color:var(--sky)}.d-low b{color:var(--ink-2)}
.d-head .org{color:var(--ink-2)}
.d-head h2{margin:8px 0 0;font-size:26px;line-height:1.2;letter-spacing:-.02em}
.facts{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.facts div{border:1px solid var(--line);border-radius:12px;padding:10px 14px;background:rgba(255,255,255,.03)}
.facts span{display:block;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink-3)}
.facts b{font-weight:600;font-size:15px}
.d-sec{border:1px solid var(--line);border-radius:16px;padding:18px 20px;background:rgba(255,255,255,.025)}
.d-sec h4{margin:0 0 10px;font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--acc)}
.d-sec h4::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--acc);margin-right:10px;vertical-align:2px}
.d-sec p{margin:0;color:var(--ink)}
.d-sec ul{margin:0;padding-left:18px;display:grid;gap:6px;color:var(--ink)}
blockquote{margin:0;padding:4px 0 4px 18px;border-left:3px solid var(--acc);font-style:italic;color:var(--ink-2)}
blockquote cite{display:block;font-style:normal;font-size:13px;color:var(--ink-3);margin-top:6px}
.msg .subj{font-size:14px;color:var(--ink-2);margin-bottom:10px}
.msg textarea{width:100%;font:15px/1.6 var(--sans);color:var(--c-ink);background:var(--cream-2);border:0;border-radius:12px;padding:14px;resize:vertical}
.d-foot{position:absolute;left:0;right:0;bottom:0;display:flex;gap:12px;padding:16px 24px;background:linear-gradient(0deg,var(--bg-2) 70%,transparent)}
.btn-gold,.btn-light{flex:1;text-align:center;border-radius:14px;padding:15px 18px;font-weight:700;font-size:15px;text-decoration:none;border:0}
.btn-gold{color:var(--bg);background:linear-gradient(160deg,var(--acc-hi),var(--acc))}
.btn-light{flex:0 0 auto;background:var(--cream);color:var(--bg)}

/* Notes */
.notes{margin-top:64px;display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.notes>*{border:1px solid var(--line);border-radius:18px;padding:24px 26px;background:rgba(255,255,255,.03);color:var(--ink-2)}
.notes h2,.notes h3{color:var(--ink);font-size:20px;margin:0 0 10px;letter-spacing:-.01em}
.notes ul,.notes ol{padding-left:20px;display:grid;gap:6px}
.notes strong,.notes b{color:var(--ink)}
.notes .box{border:0;padding:0;background:none}
footer{margin-top:48px;padding-top:20px;border-top:1px solid var(--line);font-size:14px;color:var(--ink-3)}
.foot-row{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.linkish{background:none;border:0;color:var(--ink-2);text-decoration:underline;padding:0}

@media (max-width:720px){
  .wrap{padding:0 16px 64px}
  .hero{flex-direction:column;align-items:flex-start;gap:22px;padding-top:36px}
  .medal{flex-basis:auto;width:120px;height:120px}.medal b{font-size:58px}.medal span{bottom:18px;font-size:17px}
  .filter{margin:36px -16px 0;padding:12px 16px;flex-wrap:nowrap;overflow-x:auto}
  .filter button{flex:0 0 auto}
  .grid{grid-template-columns:1fr}
  .band{padding:14px 16px;gap:14px}.band .L{font-size:36px}
  .d-body{padding:20px 18px 120px}.facts{grid-template-columns:1fr}
  .d-head{grid-template-columns:1fr;gap:10px}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
"""

JS = """
(function(){
  var store = {get:function(k){try{return localStorage.getItem(k)}catch(e){return null}},
               set:function(k,v){try{v?localStorage.setItem(k,v):localStorage.removeItem(k)}catch(e){}}};
  var root = document.documentElement;
  // Status pro Karte, bleibt nur in diesem Browser
  document.querySelectorAll('.card').forEach(function(c){
    var key = 'radar-st-' + c.dataset.id, s = store.get(key);
    if (s) c.dataset.state = s;
    c.querySelectorAll('[data-st]').forEach(function(b){
      b.addEventListener('click', function(){
        var next = c.dataset.state === b.dataset.st ? '' : b.dataset.st;
        if (next) c.dataset.state = next; else delete c.dataset.state;
        store.set(key, next); counts();
      });
    });
  });
  // Filter nach Bereich
  var cur = 'alle';
  document.querySelectorAll('.filter button').forEach(function(b){
    b.addEventListener('click', function(){
      cur = b.dataset.f;
      document.querySelectorAll('.filter button').forEach(function(x){x.setAttribute('aria-pressed', x === b)});
      document.querySelectorAll('.card').forEach(function(c){ c.hidden = !(cur === 'alle' || c.dataset.cat === cur); });
      counts();
    });
  });
  function counts(){
    document.querySelectorAll('.tier').forEach(function(t){
      var n = Array.prototype.filter.call(t.querySelectorAll('.card'), function(c){return !c.hidden && c.dataset.state !== 'skip'}).length;
      t.querySelector('.n').textContent = n + ' offen';
      t.hidden = n === 0 && !document.body.classList.contains('show-skipped');
    });
  }
  counts();
  var sk = document.getElementById('show-skipped');
  if (sk) sk.addEventListener('click', function(){
    document.body.classList.toggle('show-skipped');
    sk.textContent = document.body.classList.contains('show-skipped') ? 'Ausgeblendete wieder verstecken' : 'Ausgeblendete zeigen';
    counts();
  });
  // Anleitung ein- und ausklappen
  var g = document.querySelector('.guide'), gb = document.getElementById('guide-toggle');
  function guide(h){ g.classList.toggle('hidden', h); gb.textContent = h ? 'Anleitung zeigen' : 'Anleitung ausblenden'; gb.setAttribute('aria-expanded', !h); }
  guide(store.get('radar-guide') === 'zu');
  gb.addEventListener('click', function(){ var h = !g.classList.contains('hidden'); guide(h); store.set('radar-guide', h ? 'zu' : ''); });
  // Seitenleiste mit Details
  var body = document.querySelector('.d-body'), last = null;
  function open(uid){
    var t = document.getElementById('d-' + uid); if (!t) return;
    body.innerHTML = ''; body.appendChild(t.content.cloneNode(true)); body.scrollTop = 0;
    last = document.activeElement;
    document.body.classList.add('open-d', 'locked');
    document.getElementById('d-close').focus();
    body.querySelectorAll('[data-copy]').forEach(function(b){
      b.addEventListener('click', function(){
        var ta = document.getElementById(b.dataset.copy), lbl = b.textContent;
        var done = function(){ b.textContent = 'Kopiert ✓'; setTimeout(function(){ b.textContent = lbl }, 1800) };
        if (navigator.clipboard) navigator.clipboard.writeText(ta.value).then(done, function(){ ta.select(); b.textContent = 'Markiert, jetzt Cmd+C' });
        else { ta.select(); b.textContent = 'Markiert, jetzt Cmd+C' }
      });
    });
  }
  function close(){ document.body.classList.remove('open-d', 'locked'); if (last) last.focus(); }
  document.querySelectorAll('[data-open]').forEach(function(b){ b.addEventListener('click', function(){ open(b.dataset.open) }) });
  document.querySelectorAll('.card').forEach(function(c){
    c.addEventListener('click', function(e){ if (!e.target.closest('button,a')) open(c.id.slice(2)); });
  });
  document.getElementById('d-close').addEventListener('click', close);
  document.querySelector('.scrim').addEventListener('click', close);
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') close(); });
})();
"""


def build(profile: dict[str, Any]) -> str:
    items, newest, total, runs = load_items()
    disp = profile.get("display", {})
    name = disp.get("name", "")
    first_name = name.split(" ")[0]
    uids = {id(i): str(n) for n, i in enumerate(items)}
    by_tier = {lvl: [i for i in items if stufe(int(i.get("score") or 0))[0] == lvl] for _, lvl, _, _ in TIERS}

    top5 = "".join(
        f'<li><button type="button" data-open="{uids[id(i)]}"><span><span class="t">{esc(i.get("title"))}</span>'
        f'<span class="o">{esc(i.get("company"))}</span></span><span class="s">{int(i.get("score") or 0)}</span></button></li>'
        for i in items[:5]
    ) or '<li class="leer">Noch keine passenden Chancen. Der nächste Lauf sucht weiter, oder sag Claude, wonach du suchst.</li>'
    cats = [k for k in KAT_NAME if any(i["bucket"] == k for i in items)]
    filt = '<button type="button" data-f="alle" aria-pressed="true">Alle</button>' + "".join(
        f'<button type="button" data-f="{k}" aria-pressed="false">{esc(KAT_NAME[k])}</button>' for k in cats)

    tiers = []
    for letter, lvl, title, lead in TIERS:
        group = by_tier[lvl]
        if not group:
            continue
        cards = "".join(render_card(i, uids[id(i)]) for i in group)
        tiers.append(
            f'<section class="tier tier-{lvl}" aria-labelledby="h-{lvl}"><div class="band"><span class="L" aria-hidden="true">{letter}</span>'
            f'<div><h2 id="h-{lvl}">{title}</h2><p>{lead}</p></div><span class="n">{len(group)} offen</span></div>'
            f'<div class="grid">{cards}</div></section>')
    drawers = "".join(render_drawer(i, uids[id(i)]) for i in items)

    notes_path = DATA / "notes.html"
    notes = f'<section class="notes">{notes_path.read_text()}</section>' if notes_path.exists() else ""
    top_score = int(items[0].get("score") or 0) if items else 0

    return f"""<title>{esc(disp.get('titel', 'Chancen-Radar'))}</title>
<meta name="robots" content="noindex, nofollow">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Caveat:wght@500&family=Figtree:wght@400;500;600;700&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header class="hero">
  <div class="medal" aria-hidden="true"><b>{esc(first_name[:1])}</b><span>Radar</span></div>
  <div>
    <div class="eyebrow">Chancen-Radar · Stand {datum_de(newest)}</div>
    <h1>{esc(name)}</h1>
    <p class="sub">{esc(disp.get('untertitel', ''))}. Jede Chance ist geprüft und nach Passung sortiert.</p>
    <div class="stats">
      <div class="stat gold"><b>{top_score}</b>beste Passung</div>
      <div class="stat"><b>{len(items)}</b>passende Chancen</div>
      <div class="stat gold"><b>{len(by_tier['top'])}</b>jetzt angehen</div>
      <div class="stat"><b>{len(by_tier['mid'])}</b>genauer anschauen</div>
      <div class="stat"><b>{max(total - len(items), 0)}</b>geprüft und aussortiert</div>
    </div>
  </div>
</header>

<section class="guide" aria-labelledby="h-guide">
  <div class="guide-head"><h2 id="h-guide">So nutzt du deinen Radar</h2>
    <button type="button" class="ghost" id="guide-toggle" aria-expanded="true">Anleitung ausblenden</button></div>
  <ol>
    <li><b>Mit A anfangen</b>Die goldenen Karten passen am besten. Hier lohnt sich diese Woche jede Minute.</li>
    <li><b>Karte anklicken</b>Rechts öffnen sich alle Details: warum es passt, was verlangt wird und worauf du achten solltest.</li>
    <li><b>Nachricht kopieren</b>Für die besten Chancen liegt ein fertiger Text bereit. Kurz lesen, anpassen, abschicken.</li>
    <li><b>Status merken</b>★ merkt eine Chance, ✓ markiert sie als erledigt, ✕ blendet sie aus. Das bleibt in deinem Browser gespeichert.</li>
    <li><b>Jeden Montag neu</b>Dein Such-Agent sucht jede Woche weiter. Neue Funde tragen das Zeichen „neu“.</li>
  </ol>
</section>

<section class="top5" aria-labelledby="h-top5">
  <h2 id="h-top5">Wenn du diese Woche nur fünf Dinge machst</h2>
  <ol>{top5}</ol>
</section>

<nav class="filter" aria-label="Nach Bereich filtern">{filt}</nav>
{''.join(tiers)}
{notes}
<footer><div class="foot-row">
  <span>Gefunden von deinem Such-Agenten{f' über {runs} Läufe' if runs > 1 else ''}. Die Passung ist eine Einschätzung, keine Garantie: Anforderungen immer auf der Originalseite gegenlesen.</span>
  <button type="button" class="linkish" id="show-skipped">Ausgeblendete zeigen</button>
</div></footer>
</div>

<div class="scrim"></div>
<aside class="drawer" role="dialog" aria-modal="true" aria-label="Details zur Chance">
  <div class="d-bar"><button type="button" class="ghost" id="d-close">← Schließen</button><span>Esc schließt</span></div>
  <div class="d-body"></div>
</aside>
{drawers}
<script>{JS}</script>
"""


def main() -> int:
    profile = json.loads(PROFILE_PATH.read_text())
    page = build(profile)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(
        f'<!doctype html>\n<html lang="de"><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">\n{page}</html>\n'
    )
    print("✅ Radar gebaut → docs/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
