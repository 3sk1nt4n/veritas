#!/usr/bin/env python3
"""Render the VERITAS system (the H0 submission: Next.js on Vercel + Amazon Aurora)
as two fancy diagrams:
  - pipeline.png   : the end-to-end Veritas pipeline across the stack, with the
                     trust boundary (only deterministically validated facts cross
                     into Aurora).
  - structure.png  : the Veritas repo structure, tagged by tier
                     (Vercel web / Aurora db / async worker).

Bright warm palette. No em-dashes. chromium -> PNG @2x.
    python3 docs/build_diagrams.py
"""
import os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">')
BG = ("radial-gradient(1250px 640px at 86% -8%, rgba(255,184,58,.50), transparent 56%),"
      "radial-gradient(1100px 660px at -4% 116%, rgba(255,78,150,.44), transparent 58%),"
      "radial-gradient(1000px 580px at 50% 44%, rgba(255,214,72,.16), transparent 66%),"
      "linear-gradient(140deg,#3c1c2e 0%,#2a1430 52%,#1d1226 100%)")
BASE = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',system-ui,sans-serif;color:#fff7f2;background:{BG};position:relative;overflow:hidden}}
.mono{{font-family:'JetBrains Mono',ui-monospace,monospace}}
.corner{{position:absolute;width:40px;height:40px;border:2.5px solid rgba(255,206,90,.9);box-shadow:0 0 16px rgba(255,196,70,.7);z-index:5}}
.ctl{{top:20px;left:20px;border-right:0;border-bottom:0}}.ctr{{top:20px;right:20px;border-left:0;border-bottom:0}}
.cbl{{bottom:20px;left:20px;border-right:0;border-top:0}}.cbr{{bottom:20px;right:20px;border-left:0;border-top:0}}
h1{{font-size:35px;font-weight:800;letter-spacing:-.6px;
  background:linear-gradient(92deg,#ffe14d,#ffa12e 42%,#ff4d8d 78%,#e879f9);-webkit-background-clip:text;background-clip:text;
  color:transparent;filter:drop-shadow(0 0 28px rgba(255,180,60,.6))}}
.sub{{color:#ffe0cf;font-size:15.5px;margin-top:7px;max-width:1180px;line-height:1.45}}
.sub b{{color:#ffd45e}}
.amber{{color:#ffc04d}} .pink{{color:#ff6fa5}} .gold{{color:#ffd45e}} .cyan{{color:#34e0e0}} .violet{{color:#c9a2ff}}
"""
CORNERS = '<div class="corner ctl"></div><div class="corner ctr"></div><div class="corner cbl"></div><div class="corner cbr"></div>'


def render(name, w, h, body, css):
    html = f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{BASE}{css}</style></head><body>{CORNERS}{body}</body></html>'
    hp = os.path.join(HERE, f"{name}.html"); pp = os.path.join(HERE, f"{name}.png")
    open(hp, "w").write(html)
    subprocess.run(["chromium", "--headless=new", "--no-sandbox", "--hide-scrollbars",
                    "--force-device-scale-factor=3", f"--window-size={w},{h}",
                    "--virtual-time-budget=5000", "--default-background-color=ff1d1226",
                    f"--screenshot={pp}", f"file://{hp}"], capture_output=True)
    print(f"rendered {pp} ({os.path.getsize(pp)//1024} KB)")


# ----------------------- VERITAS END-TO-END PIPELINE -----------------------
# (num, tier, tier_class, title, detail)
STAGES_TOP = [  # untrusted side (evidence + AI engine)
    ("1", "Amazon S3", "amber", "Evidence lands in S3",
     "memory image, disk image, event logs - the raw case material"),
    ("2", "Engine worker (ECS / EC2)", "pink", "Sentinel engine runs the 16-step investigation",
     "the AI proposes findings; deterministic code re-checks every claim - the AI is trusted with nothing"),
]
STAGES_BOT = [  # trusted side (Aurora system of record + Vercel app)
    ("3", "Ingest adapter", "gold", "Only validated facts are written to Aurora",
     "bulk UPSERT with ON CONFLICT (fact_signature) - cross-tool corroboration merges in one statement"),
    ("4", "Amazon Aurora PostgreSQL (Serverless v2)", "gold", "Aurora is the system of record",
     "cases, evidence, tool_runs, facts, findings, claims - chain-of-custody by foreign key, ~19 indexes, RLS, recursive CTEs"),
    ("5", "Next.js on Vercel", "cyan", "The front end queries Aurora directly",
     "server components run pooled SQL over SSL - dashboards, the claim->fact->tool trace, the cross-case pivot"),
    ("6", "Analyst, in the browser", "violet", "Every finding traces to proof",
     "verdict + disposition, the AI-overruled view, one-click proof chain, cross-case IOC pivot, queue a new run"),
]


def stage_row(num, tier, cls, title, detail):
    return (f'<div class="stage {cls}"><div class="num {cls}">{num}</div>'
            f'<div class="scard"><div class="stier {cls}">{tier}</div>'
            f'<div class="st">{title}</div><div class="sd">{detail}</div></div></div>')


def pipeline():
    top = "".join(stage_row(*s) for s in STAGES_TOP)
    bot = "".join(stage_row(*s) for s in STAGES_BOT)
    body = f"""
    <div class="wrap">
      <h1>Veritas - end-to-end pipeline</h1>
      <div class="sub">How one investigation flows across the stack. Raw evidence and raw model output never reach the database or the web app; <b>only deterministically validated facts cross the trust boundary into Amazon Aurora</b>.</div>
      <div class="flow">
        {top}
        <div class="boundary"><span class="bt">TRUST BOUNDARY</span><span class="bd">only validated facts cross into Aurora - raw evidence and raw AI output stay on the engine side</span></div>
        {bot}
      </div>
      <div class="loop"><b>New-run loop:</b> the Vercel app inserts a job into a <span class="mono">runs_queue</span> table in Aurora; the worker claims it with <span class="mono">SELECT ... FOR UPDATE SKIP LOCKED</span> (no broker) and the flow repeats from step 2.</div>
    </div>"""
    css = """
    .wrap{padding:40px 64px}
    .flow{margin-top:22px;display:flex;flex-direction:column;gap:13px}
    .stage{display:flex;align-items:stretch;gap:18px}
    .num{flex:0 0 auto;width:52px;border-radius:13px;display:grid;place-items:center;font-weight:800;font-size:22px;
      font-family:'JetBrains Mono',monospace;color:#1a0f10;border:0}
    .num.amber{background:linear-gradient(180deg,#ffd97a,#ffb347)}
    .num.pink{background:linear-gradient(180deg,#ff86b3,#ff4d8d);color:#2a0a18}
    .num.gold{background:linear-gradient(180deg,#ffe06a,#ffc31f)}
    .num.cyan{background:linear-gradient(180deg,#7df2f2,#34d0d0);color:#06201f}
    .num.violet{background:linear-gradient(180deg,#d6b8ff,#a987ff);color:#1c0f33}
    .scard{flex:1;border:1px solid;border-radius:13px;padding:13px 20px;
      background:linear-gradient(180deg,rgba(86,52,64,.86),rgba(56,32,46,.8));box-shadow:0 14px 36px -20px rgba(0,0,0,.55),0 1px 0 0 rgba(255,255,255,.14) inset}
    .stage.amber .scard{border-color:rgba(255,192,77,.6)} .stage.pink .scard{border-color:rgba(255,104,160,.7);background:linear-gradient(180deg,rgba(104,42,68,.86),rgba(74,30,52,.8))}
    .stage.gold .scard{border-color:rgba(255,190,76,.75);background:linear-gradient(180deg,rgba(98,60,26,.86),rgba(66,40,18,.8))}
    .stage.cyan .scard{border-color:rgba(52,224,224,.6);background:linear-gradient(180deg,rgba(20,60,64,.86),rgba(14,42,46,.8))}
    .stage.violet .scard{border-color:rgba(201,162,255,.6);background:linear-gradient(180deg,rgba(60,42,92,.86),rgba(40,28,64,.8))}
    .stier{font-size:12px;text-transform:uppercase;letter-spacing:1.3px;font-weight:700}
    .stier.amber{color:#ffc04d}.stier.pink{color:#ff8fb3}.stier.gold{color:#ffd45e}.stier.cyan{color:#5ce6e6}.stier.violet{color:#cdb0ff}
    .st{font-size:20px;font-weight:700;color:#fff;margin-top:2px}
    .sd{font-size:13.5px;color:#ffe6d8;margin-top:4px;line-height:1.4}
    .boundary{margin:5px 0 5px 70px;border:1.5px dashed rgba(255,104,160,.85);border-radius:11px;padding:11px 18px;
      background:rgba(255,104,160,.13);display:flex;align-items:center;gap:16px;box-shadow:0 0 40px -12px rgba(255,78,150,.5) inset}
    .bt{font-weight:800;letter-spacing:2px;color:#ffe14d;font-size:15px;white-space:nowrap}
    .bd{color:#ffdfe9;font-size:14px}
    .loop{margin-top:18px;border-left:3px solid rgba(255,206,90,.8);padding:6px 0 6px 16px;color:#ffe6d8;font-size:14.5px;line-height:1.45}
    .loop b{color:#ffd45e}
    """
    render("pipeline", 1440, 1020, body, css)


# ----------------------- VERITAS PROJECT STRUCTURE -----------------------
# (indent, path, role, tier '' | 'vercel' | 'aurora' | 'worker' | 'docs')
TREE = [
    (0, "veritas/", "the H0 submission - Next.js on Vercel + Amazon Aurora PostgreSQL", ""),
    (1, "web/", "VERCEL - Next.js 15 App Router front end", "vercel"),
    (2, "app/page.tsx", "cases landing + portfolio stats", "vercel"),
    (2, "app/case/[caseId]/ ...", "dashboard, findings grid, finding trace (the hero)", "vercel"),
    (2, "app/pivot/page.tsx", "cross-case IOC pivot", "vercel"),
    (2, "app/runs/ + app/api/runs/", "queue a new investigation + enqueue API", "vercel"),
    (2, "components/  +  lib/", "trace tree, scoreboard, RunsLive . db.ts pool + typed SQL", "vercel"),
    (1, "db/", "AURORA - the data of record", "aurora"),
    (2, "schema.sql", "chain-of-custody model, ~19 indexes, RLS, recursive CTEs", "aurora"),
    (2, "demo_queries.sql", "the trust-layer queries (overrule / trace / pivot / merge)", "aurora"),
    (1, "ingest/", "ASYNC WORKER - off Vercel", "worker"),
    (2, "ingest.py", "load validated facts into Aurora (count-fidelity gate)", "worker"),
    (2, "worker.py", "Postgres-as-queue (SELECT FOR UPDATE SKIP LOCKED)", "worker"),
    (1, "docs/", "architecture, pipeline, structure, submission, demo, blog", "docs"),
]


def structure():
    GLY = {"vercel": "&#9650;", "aurora": "&#9632;", "worker": "&#9670;", "docs": "&#8226;", "": "&#9656;"}
    CLS = {"vercel": "cyan", "aurora": "gold", "worker": "pink", "docs": "violet", "": "amber"}
    rows = []
    for indent, path, role, tier in TREE:
        pad = 30 * indent
        isdir = path.endswith("/")
        rows.append(
            f'<div class="trow" style="padding-left:{pad}px">'
            f'<span class="dot {CLS[tier]}">{GLY[tier]}</span>'
            f'<span class="path {"dir" if isdir else "file"}">{path}</span>'
            f'<span class="role">{role}</span></div>')
    body = f"""
    <div class="wrap">
      <h1>Veritas - project structure</h1>
      <div class="sub">The submission is one repo with three tiers: the <b>Vercel</b> front end, the <b>Amazon Aurora</b> schema, and an <b>async worker</b> that ingests only validated facts.</div>
      <div class="tree">{''.join(rows)}</div>
      <div class="legend">
        <span><span class="dot cyan">&#9650;</span> Vercel (Next.js)</span>
        <span><span class="dot gold">&#9632;</span> Amazon Aurora PostgreSQL</span>
        <span><span class="dot pink">&#9670;</span> async worker</span>
        <span><span class="dot violet">&#8226;</span> docs</span>
      </div>
    </div>"""
    css = """
    .wrap{padding:46px 72px}
    .tree{margin-top:26px;border:1px solid rgba(255,196,120,.35);border-radius:16px;padding:24px 30px;
      background:linear-gradient(180deg,rgba(72,42,54,.62),rgba(48,28,40,.55));box-shadow:0 1px 0 0 rgba(255,255,255,.10) inset}
    .trow{display:flex;align-items:center;gap:14px;padding:8px 0;font-size:18px}
    .dot{width:22px;text-align:center;font-size:15px}
    .path{font-family:'JetBrains Mono',monospace;font-size:17.5px}
    .path.dir{font-weight:700} .path.file{color:#f3e3da}
    .role{color:#ffdccb;font-size:14.5px}
    .cyan{color:#5ce6e6}.gold{color:#ffd45e}.pink{color:#ff8fb3}.violet{color:#cdb0ff}.amber{color:#ffc04d}
    .path.dir{color:#ffe0cf}
    .legend{margin-top:24px;display:flex;gap:34px;font-size:15px;color:#ffe0cf}
    .legend .dot{margin-right:6px}
    """
    render("structure", 1440, 1020, body, css)


if __name__ == "__main__":
    pipeline()
    structure()
