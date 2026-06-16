#!/usr/bin/env python3
"""Render the REAL Sentinel Ensemble architecture as two fancy diagrams:
  - pipeline.png   : Step 0 to 16 across the TRUST BOUNDARY
                     (untrusted-AI zone | boundary | trusted-deterministic zone)
  - structure.png  : the project structure, modules tagged by trust zone

Grounded in ARCHITECTURE.md (Step 0-16, the 5 AI invocations, the trust split)
and the real repo layout. Bright warm palette; AI = pink/magenta ("trusted with
nothing"), deterministic = cyan ("trusted"). No em-dashes. chromium -> PNG @2x.

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
.sub{{color:#ffe0cf;font-size:15px;margin-top:6px}}
.pink{{color:#ff6fa5}} .cyan{{color:#34e0e0}} .orange{{color:#ff9d3d}}
.corners{{}}
"""
CORNERS = '<div class="corner ctl"></div><div class="corner ctr"></div><div class="corner cbl"></div><div class="corner cbr"></div>'


def render(name, w, h, body, css):
    html = f'<!doctype html><html><head><meta charset="utf-8">{FONTS}<style>{BASE}{css}</style></head><body>{CORNERS}{body}</body></html>'
    hp = os.path.join(HERE, f"{name}.html"); pp = os.path.join(HERE, f"{name}.png")
    open(hp, "w").write(html)
    subprocess.run(["chromium", "--headless=new", "--no-sandbox", "--hide-scrollbars",
                    "--force-device-scale-factor=2", f"--window-size={w},{h}",
                    "--virtual-time-budget=5000", "--default-background-color=ff0c0710",
                    f"--screenshot={pp}", f"file://{hp}"], capture_output=True)
    print(f"rendered {pp} ({os.path.getsize(pp)//1024} KB)")


# ----------------------------- PIPELINE -----------------------------
# (num, side 'ai'|'det', title, detail)
STEPS = [
    ("0",   "det", "Onboarding", "findevil.sh - read-only mount, OS probe, SHA256 precompute, depth select"),
    ("1",   "det", "Pipeline start", "the conductor takes over: 'tell me what happened on this system'"),
    ("2",   "det", "SHA256 fingerprint #1", "warm-start from precomputed, size-verified hashes"),
    ("3",   "det", "SSDT rootkit check", "kernel integrity verified before any process is trusted"),
    ("4",   "det", "Tool-selection prep", "195-tool typed catalog built - zero tools run yet"),
    ("5",   "ai",  "Invocation 1 - Tool selection", "the AI picks an investigation set; 31K guardrails applied after"),
    ("6",   "det", "MCP server runs tools", "Vol3 / Sleuth Kit / EZ Tools - typed JSON in and out, never a shell"),
    ("7",   "det", "EvidenceDB + reference set", "typed facts reconciled across families, with provenance"),
    ("8-9", "ai",  "Invocation 2 - Analysis", "4-model ensemble proposes candidate findings; consensus tracked"),
    ("10",  "det", "Deterministic validator", "every claim checked vs the reference set - 6 claim types"),
    ("11",  "ai",  "Invocation 3 - ReAct threads", "re-investigates its own findings with live tools, overturns its verdicts"),
    ("12",  "det", "Self-correction routing", "deterministic claim rescue - blocked is never silently dropped"),
    ("13",  "det", "Confidence calibration", "3+ artifact types = HIGH; entity reconcile; disposition buckets"),
    ("13AA","ai",  "AI finalize (inv3a)", "final re-judge of every non-terminal finding; code denies unproven promotions"),
    ("14",  "ai",  "Invocation 4 - Report", "narrative from validated buckets only; citations required"),
    ("15",  "det", "SHA256 fingerprint #2", "must equal #1 - evidence-spoliation check"),
    ("16",  "det", "Delivered", "narrative, findings table, FP table, IOC roll-up, audit trail"),
]


def pipeline():
    rows = []
    for num, side, title, detail in STEPS:
        card = (f'<div class="card {side}"><div class="t">{title}</div><div class="d">{detail}</div></div>')
        badge = f'<div class="num {side}">{num}</div>'
        if side == "ai":
            rows.append(f'<div class="step"><div class="slot l">{card}</div>{badge}<div class="slot r"></div></div>')
        else:
            rows.append(f'<div class="step"><div class="slot l"></div>{badge}<div class="slot r">{card}</div></div>')
    body = f"""
    <div class="wrap">
      <h1>The pipeline - Step 0 to 16</h1>
      <div class="sub">One deterministic conductor (<span class="mono">run_pipeline.py</span>) drives 16 steps and summons the AI exactly 5 times. The AI is a brilliant but untrusted soloist: it reasons, but it is trusted with nothing.</div>
      <div class="zones">
        <div class="zhead l"><div class="zt pink">&#8623; UNTRUSTED-AI ZONE &#8623;</div><div class="zd">Claude / LLM invocations - reasons, proposes, drafts; <b>trusted with nothing</b></div></div>
        <div class="zhead c"><div class="bt">TRUST<br>BOUNDARY</div><div class="zd" style="text-align:center">every claim re-checked as it crosses</div></div>
        <div class="zhead r"><div class="zt cyan">&#8624; TRUSTED DETERMINISTIC ZONE &#8624;</div><div class="zd">Python conductor - owns memory, <b>no shell tools</b>, re-checks every claim, ships output</div></div>
      </div>
      <div class="flow"><div class="spine"></div>{''.join(rows)}</div>
    </div>"""
    css = """
    .wrap{padding:40px 60px}
    .zones{display:grid;grid-template-columns:1fr 150px 1fr;gap:16px;margin:22px 0 14px;align-items:end}
    .zhead .zt{font-size:16px;font-weight:800;letter-spacing:1px}
    .zhead .zd{font-size:12.5px;color:#d9c3cd;margin-top:5px;line-height:1.35}
    .zhead.l{text-align:right}.zhead .zd b{color:#fff}
    .bt{font-size:14px;font-weight:800;letter-spacing:2px;color:#ffd0a0;text-align:center;line-height:1.1}
    .flow{position:relative}
    .spine{position:absolute;left:50%;top:0;bottom:0;width:3px;transform:translateX(-50%);
      background:linear-gradient(180deg,#ff9d3d,#ff4d8d 45%,#34e0e0);box-shadow:0 0 16px rgba(255,77,141,.55);border-radius:3px;z-index:1}
    .step{display:grid;grid-template-columns:1fr 150px 1fr;gap:16px;align-items:center;margin-bottom:9px;position:relative;z-index:2}
    .slot{display:flex}.slot.l{justify-content:flex-end}.slot.r{justify-content:flex-start}
    .num{justify-self:center;min-width:50px;height:40px;padding:0 10px;border-radius:11px;display:grid;place-items:center;
      font-weight:800;font-size:15px;font-family:'JetBrains Mono',monospace;border:1.5px solid;background:#140a12}
    .num.ai{color:#ff6fa5;border-color:rgba(255,77,141,.7);box-shadow:0 0 16px -3px rgba(255,77,141,.7)}
    .num.det{color:#34e0e0;border-color:rgba(52,224,224,.6);box-shadow:0 0 16px -4px rgba(52,224,224,.5)}
    .card{max-width:560px;border:1px solid;border-radius:11px;padding:9px 14px}
    .card.ai{border-color:rgba(255,104,160,.65);text-align:right;background:linear-gradient(180deg,rgba(104,42,68,.86),rgba(74,30,52,.8));
      box-shadow:0 0 0 1px rgba(255,104,160,.16),0 12px 32px -16px rgba(255,78,150,.65),0 1px 0 0 rgba(255,255,255,.14) inset}
    .card.det{border-color:rgba(52,224,224,.52);background:linear-gradient(180deg,rgba(20,60,64,.84),rgba(14,42,46,.78));
      box-shadow:0 0 0 1px rgba(52,224,224,.14),0 12px 32px -16px rgba(52,224,224,.5),0 1px 0 0 rgba(255,255,255,.12) inset}
    .card .t{font-weight:700;font-size:16px;color:#fff}
    .card .d{font-size:12px;color:#e7d0c6;margin-top:2px;line-height:1.3}
    .card.det .d{color:#cfe6e6}
    """
    render("pipeline", 1440, 1480, body, css)


# ----------------------------- STRUCTURE -----------------------------
# (indent, path, role, zone 'ai'|'det'|'seam'|'')
TREE = [
    (0, "Sentinel-Ensemble/", "", ""),
    (1, "findevil.sh", "entry - dependency checks, friendly errors", "det"),
    (1, "step0_onboard.py", "onboarding - one question: where is the evidence", "det"),
    (1, "run_pipeline.py", "THE CONDUCTOR - drives all 16 steps", "det"),
    (1, "src/sift_sentinel/", "", ""),
    (2, "coordinator.py", "orchestration + AI-invocation wiring", "det"),
    (2, "ensemble.py", "Invocation 2 - 4-model analysis ensemble", "ai"),
    (2, "react_verdicts.py", "Invocation 3 - ReAct self-correction (Layer 1)", "ai"),
    (2, "correction/  (4)", "self-correction routing + finalize (Layer 2)", "ai"),
    (2, "analysis/  (54)", "EvidenceDB typed facts, entity reconcile, confidence, disposition", "det"),
    (2, "validation/  (9)", "deterministic validator - re-checks every claim", "det"),
    (2, "tools/  (22) + server.py", "195 typed forensic tools on an MCP server - ZERO shell", "det"),
    (2, "reporting/  (17)", "Invocation 4 - narrative, findings tables, HTML", "det"),
    (2, "llm_provider.py", "provider seam - Anthropic / Qwen (pluggable)", "seam"),
    (2, "model_roles.py . prompts.py . entities.py . schema/", "model routing, prompts, typed entities", "det"),
    (1, "tests/  (4,800+)", "regression + acceptance gates", "det"),
]


def structure():
    GLYPH = {"ai": "&#9670;", "det": "&#9632;", "seam": "&#9672;", "": ""}
    ZCLS = {"ai": "pink", "det": "cyan", "seam": "orange", "": ""}
    rows = []
    for indent, path, role, zone in TREE:
        pad = 26 * indent
        isdir = path.endswith("/")
        pcls = "dir" if isdir else "file"
        tag = f'<span class="dot {ZCLS[zone]}">{GLYPH[zone]}</span>' if zone else ""
        rl = f'<span class="role">{role}</span>' if role else ""
        rows.append(f'<div class="trow" style="padding-left:{pad}px">{tag}<span class="path {pcls}">{path}</span>{rl}</div>')
    body = f"""
    <div class="wrap">
      <h1>Project structure</h1>
      <div class="sub">~78k lines of Python. The conductor and the deterministic trust layer own the pipeline; the AI is summoned only by the modules tagged <span class="pink">&#9670; AI</span>.</div>
      <div class="tree">{''.join(rows)}</div>
      <div class="legend">
        <span><span class="dot cyan">&#9632;</span> trusted deterministic</span>
        <span><span class="dot pink">&#9670;</span> AI invocation (untrusted)</span>
        <span><span class="dot orange">&#9672;</span> provider seam (Anthropic / Qwen)</span>
      </div>
    </div>"""
    css = """
    .wrap{padding:46px 70px}
    .tree{margin-top:26px;border:1px solid rgba(255,196,120,.35);border-radius:16px;padding:22px 28px;
      background:linear-gradient(180deg,rgba(72,42,54,.62),rgba(48,28,40,.55));box-shadow:0 1px 0 0 rgba(255,255,255,.10) inset}
    .trow{display:flex;align-items:center;gap:12px;padding:7px 0;font-size:18px}
    .dot{width:22px;text-align:center;font-size:14px}
    .path{font-family:'JetBrains Mono',monospace;font-size:17px}
    .path.dir{color:#ffd0a0;font-weight:600}.path.file{color:#f3e3da}
    .role{color:#cbb3bf;font-size:14px}
    .pink{color:#ff6fa5}.cyan{color:#34e0e0}.orange{color:#ff9d3d}
    .legend{margin-top:22px;display:flex;gap:34px;font-size:15px;color:#e7c2b6}
    .legend .dot{margin-right:6px}
    """
    render("structure", 1440, 1020, body, css)


if __name__ == "__main__":
    pipeline()
    structure()
