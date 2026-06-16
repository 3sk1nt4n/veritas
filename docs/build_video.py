#!/usr/bin/env python3
"""Build the Veritas demo video: a motion deck (slides crossfade in) in the
app's investigation-console aesthetic.

Pipeline: render each slide HTML -> PNG (chromium), then ffmpeg crossfades them
into docs/veritas-demo.mp4 (1920x1080, H.264, YouTube-ready).

Re-run anytime. Drop an RDS console screenshot at docs/assets/rds.png and it gets
embedded into the Aurora-proof slide automatically.

    python3 docs/build_video.py
"""
from __future__ import annotations
import base64, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots")
BUILD = os.path.join(HERE, "video_build")
OUT = os.path.join(HERE, "veritas-demo.mp4")
os.makedirs(BUILD, exist_ok=True)

CHROMIUM = "chromium"
W, H, FPS, XFADE = 1920, 1080, 30, 0.7


def data_uri(path: str) -> str:
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden;font-family:'Inter',system-ui,Arial,sans-serif;color:#e6edf6}
body{background:
  radial-gradient(1400px 700px at 82% -10%, rgba(34,211,238,.12), transparent 60%),
  radial-gradient(1000px 600px at 0% 0%, rgba(167,139,250,.09), transparent 55%),
  #070a10;display:flex;flex-direction:column;justify-content:center;padding:0 130px;position:relative}
.mono{font-family:'JetBrains Mono',ui-monospace,monospace}
.kicker{font-size:24px;letter-spacing:5px;text-transform:uppercase;color:#67e8f9;margin-bottom:26px;font-weight:600}
.brandmark{position:absolute;top:54px;left:130px;display:flex;align-items:center;gap:14px;color:#8597b3;font-size:22px}
.brandmark .b{width:30px;height:30px;border-radius:8px;border:1px solid rgba(34,211,238,.5);background:rgba(34,211,238,.12);
  color:#22d3ee;display:grid;place-items:center;font-size:18px}
.foot{position:absolute;bottom:48px;left:130px;right:130px;display:flex;justify-content:space-between;color:#5f7characters;font-size:19px;color:#6b7d99}
h1.cover{font-size:140px;font-weight:800;letter-spacing:-3px;line-height:.95}
.cover-sub{font-size:42px;color:#aab8cf;margin-top:30px;max-width:1300px;line-height:1.3}
.cover .c{color:#22d3ee}
h2{font-size:62px;font-weight:700;letter-spacing:-1px;line-height:1.08;max-width:1400px}
.big{font-size:88px;font-weight:800;letter-spacing:-2px;line-height:1.02;max-width:1500px}
.big .c{color:#22d3ee}
.sub{font-size:36px;color:#aab8cf;margin-top:34px;max-width:1400px;line-height:1.4}
.rows{margin-top:50px;display:flex;flex-direction:column;gap:22px;max-width:1620px}
.row{display:flex;gap:30px;align-items:flex-start;border:1px solid #1e2a40;border-radius:16px;
  background:rgba(15,22,35,.6);padding:24px 30px}
.row .tag{min-width:300px;font-size:30px;font-weight:700;color:#22d3ee}
.row .ans{font-size:28px;color:#cdd8ea;line-height:1.35}
ul.bul{margin-top:46px;display:flex;flex-direction:column;gap:26px;max-width:1560px}
ul.bul li{list-style:none;display:flex;gap:20px;font-size:33px;color:#cdd8ea;line-height:1.32}
ul.bul li::before{content:"";flex:0 0 auto;margin-top:16px;width:12px;height:12px;border-radius:50%;
  background:#22d3ee;box-shadow:0 0 14px #22d3ee}
ul.bul b{color:#fff}
.split{display:flex;gap:70px;align-items:center}
.split .txt{flex:0 0 660px}
.split .txt h2{font-size:54px}
.split .txt .lines{font-size:31px;color:#aab8cf;margin-top:26px;line-height:1.4}
.window{flex:1;border:1px solid #233149;border-radius:16px;overflow:hidden;background:#0b0f17;
  box-shadow:0 40px 90px -30px rgba(0,0,0,.9), 0 0 0 1px rgba(34,211,238,.08)}
.window .bar{height:54px;display:flex;align-items:center;gap:10px;padding:0 20px;background:#0f1623;border-bottom:1px solid #1e2a40}
.window .bar .dot{width:13px;height:13px;border-radius:50%}
.window .urlpill{margin-left:18px;flex:1;height:32px;border-radius:8px;background:#070a10;border:1px solid #1e2a40;
  display:flex;align-items:center;padding:0 14px;color:#8597b3;font-size:18px}
.window .shotwrap{height:760px;overflow:hidden}
.window img{width:100%;display:block}
.full-img{position:absolute;inset:0;display:grid;place-items:center}
.full-img img{max-width:1660px;max-height:840px;border:1px solid #233149;border-radius:14px;
  box-shadow:0 40px 90px -30px rgba(0,0,0,.9)}
.cap{position:absolute;bottom:70px;left:0;right:0;text-align:center;font-size:30px;color:#aab8cf;padding:0 200px}
.proofcard{margin-top:46px;border:1px solid rgba(34,211,238,.35);border-radius:18px;background:rgba(11,30,40,.55);
  padding:40px 46px;max-width:1500px}
.proofcard .pl{font-size:30px;color:#cdd8ea;line-height:1.5}
.proofcard .pl b{color:#67e8f9}
.links{margin-top:40px;font-size:34px;color:#8597b3}
.links .u{color:#67e8f9}
.tag-pill{display:inline-block;margin-top:40px;border:1px solid rgba(34,211,238,.4);background:rgba(34,211,238,.1);
  color:#67e8f9;border-radius:999px;padding:14px 30px;font-size:30px;font-weight:600}
"""

BRAND = '<div class="brandmark"><span class="b">&#10003;</span> Veritas</div>'
HEAD = ('<!doctype html><html><head><meta charset="utf-8">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">'
        f'<style>{CSS}</style></head><body>')
TAIL = "</body></html>"


def cover(kicker, title_html, sub):
    return (f'{BRAND}<div class="kicker">{kicker}</div>'
            f'<h1 class="cover">{title_html}</h1><div class="cover-sub">{sub}</div>'
            f'<div class="foot"><span>github.com/3sk1nt4n/veritas</span><span>veritas-rouge.vercel.app</span></div>')


def statement(kicker, big_html, sub):
    return f'{BRAND}<div class="kicker">{kicker}</div><div class="big">{big_html}</div><div class="sub">{sub}</div>'


def full(img, caption):
    return f'{BRAND}<div class="full-img"><img src="{img}"></div><div class="cap">{caption}</div>'


def criteria(title, rows):
    r = "".join(f'<div class="row"><div class="tag">{t}</div><div class="ans">{a}</div></div>' for t, a in rows)
    return f'{BRAND}<h2>{title}</h2><div class="rows">{r}</div>'


def bullets(title, items):
    li = "".join(f"<li><span>{x}</span></li>" for x in items)
    return f'{BRAND}<h2>{title}</h2><ul class="bul">{li}</ul>'


def shot(kicker, title, lines, url, img):
    return (f'{BRAND}<div class="split"><div class="txt"><div class="kicker">{kicker}</div>'
            f'<h2>{title}</h2><div class="lines">{lines}</div></div>'
            f'<div class="window"><div class="bar">'
            f'<span class="dot" style="background:#ff5f57"></span><span class="dot" style="background:#febc2e"></span>'
            f'<span class="dot" style="background:#28c840"></span>'
            f'<span class="urlpill mono">{url}</span></div>'
            f'<div class="shotwrap"><img src="{img}"></div></div></div>')


def aurora_proof():
    rds = os.path.join(HERE, "assets", "rds.png")
    if os.path.exists(rds):
        return full(data_uri(rds), "Amazon Aurora PostgreSQL Serverless v2 (us-east-1) - the cluster behind every screen.")
    return (f'{BRAND}<div class="kicker">Real cloud database</div>'
            f'<h2>Amazon Aurora PostgreSQL<br>Serverless v2 &middot; us-east-1</h2>'
            f'<div class="proofcard"><div class="pl">'
            f'Cluster <b>veritas-db</b> &middot; direct connection from Vercel (SSL).<br>'
            f'<b>3</b> real cases &middot; <b>2,257</b> typed facts ingested &middot; <b>144</b> findings &middot; <b>11</b> AI-overruled-by-code.<br>'
            f'Every screen you just saw is a live SQL query against this cluster.</div></div>')


SLIDES = [
    (4.6, cover("H0 &middot; Track 2 (B2B) &middot; Amazon Aurora PostgreSQL + Vercel",
                'VERI<span class="c">TAS</span>',
                'The investigation platform where <span class="c">the AI never gets the final word.</span>')),
    (6.0, full(data_uri(os.path.join(HERE, "architecture.png")),
               "The pipeline: a Vercel front end, Amazon Aurora as the system of record, an engine worker behind a trust boundary.")),
    (5.4, statement("The problem",
                    'You can&rsquo;t ship an AI conclusion <span class="c">you can&rsquo;t audit.</span>',
                    "In security, fraud, and compliance, an AI that occasionally hallucinates is worthless in front of a court, an insurer, or a regulator.")),
    (5.4, statement("The idea",
                    'So we flipped it. <span class="c">Deterministic code gets the final word.</span>',
                    "An agent investigates end to end, but code (not the model) decides what is confirmed, and every finding traces by foreign key to the tool that proved it.")),
    (8.5, criteria("How Veritas answers the brief", [
        ("Technological", "A deliberate Aurora data model: FK chain-of-custody, a SHA-1 ON CONFLICT merge, ~19 real indexes, recursive CTEs, RLS, Serverless v2."),
        ("Design", "A focused investigation console where the front end is designed around the data - the claim&rarr;fact&rarr;tool trace is the product."),
        ("Impact", "SOC teams, DFIR firms, and insurers who can&rsquo;t trust hallucinating AI get an auditable, shippable system."),
        ("Originality", "&lsquo;The AI never gets the final word&rsquo; isn&rsquo;t a slogan - it&rsquo;s an ai_overruled column and a foreign key you can query."),
    ])),
    (8.0, bullets("Why Amazon Aurora PostgreSQL", [
        "<b>Foreign keys enforce the chain of custody</b> - a finding can&rsquo;t cite proof that doesn&rsquo;t exist.",
        "<b>A SHA-1 fact_signature UNIQUE</b> turns cross-tool corroboration into an ON CONFLICT merge.",
        "<b>The engine&rsquo;s ~19 pivot indexes become real Postgres indexes</b> (btree, GIN, pg_trgm).",
        "<b>A recursive CTE</b> walks the process tree; a materialized view powers cross-case pivots.",
        "<b>Serverless v2</b> scales down between investigations - about a dollar a day.",
    ])),
    (5.2, shot("Case dashboard", "Verdict, integrity, disposition.",
               "A SHA-256 &lsquo;evidence unmodified&rsquo; badge - and the headline: the AI was overruled 4&times; by deterministic code.",
               "veritas-rouge.vercel.app/case/&hellip;", data_uri(os.path.join(SHOTS, "02-dashboard.png")))),
    (6.0, shot("The trust layer", "The AI proposed CONFIRMED. The code said SUSPICIOUS.",
               "With the exact gate that withheld promotion. Nothing is silently dropped.",
               "&hellip;/finding/F001", data_uri(os.path.join(SHOTS, "03-overruled-hero.png")))),
    (5.4, shot("Proof chain", "Every claim &rarr; validated fact &rarr; source tool.",
               "One finding_trace() query. The raw forensic-tool output is right there.",
               "&hellip;/finding/F008", data_uri(os.path.join(SHOTS, "04-trace.png")))),
    (5.4, shot("Cross-case pivot", "One indexed query across every case.",
               "Type a hash, IP, or PID - Aurora returns every case it appears in. The file-based engine cannot.",
               "&hellip;/pivot", data_uri(os.path.join(SHOTS, "05-pivot.png")))),
    (5.0, shot("New investigation", "Postgres is the queue.",
               "Enqueue a run; a worker claims it with SELECT FOR UPDATE SKIP LOCKED and streams 16-step progress.",
               "&hellip;/runs", data_uri(os.path.join(SHOTS, "06-runs.png")))),
    (5.4, aurora_proof()),
    (5.2, cover("", 'The AI never gets <span class="c">the final word.</span>',
                '<span class="links"><span class="u">veritas-rouge.vercel.app</span> &middot; github.com/3sk1nt4n/veritas</span>'
                '<br><span class="tag-pill">#H0Hackathon</span>')),
]


def render():
    pngs = []
    for i, (_d, body) in enumerate(SLIDES):
        html_path = os.path.join(BUILD, f"slide_{i:02d}.html")
        png_path = os.path.join(BUILD, f"slide_{i:02d}.png")
        with open(html_path, "w") as f:
            f.write(HEAD + body + TAIL)
        cmd = [CHROMIUM, "--headless=new", "--no-sandbox", "--hide-scrollbars",
               "--force-device-scale-factor=1", f"--window-size={W},{H}",
               "--virtual-time-budget=5000", "--default-background-color=ff070a10",
               f"--screenshot={png_path}", f"file://{html_path}"]
        subprocess.run(cmd, capture_output=True)
        if not os.path.exists(png_path):
            print(f"FAILED to render slide {i}", file=sys.stderr); sys.exit(1)
        pngs.append(png_path)
        print(f"rendered slide {i:02d} ({SLIDES[i][0]}s)")
    return pngs


def stitch(pngs):
    durs = [d for d, _ in SLIDES]
    inputs = []
    for p, d in zip(pngs, durs):
        inputs += ["-loop", "1", "-t", f"{d}", "-i", p]
    fc = []
    for i in range(len(pngs)):
        fc.append(f"[{i}:v]scale={W}:{H}:force_original_aspect_ratio=decrease,"
                  f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x070a10,setsar=1,fps={FPS},format=yuv420p[v{i}]")
    prev = "v0"
    cumulative = durs[0]
    for i in range(1, len(pngs)):
        offset = cumulative - XFADE
        out = f"x{i}"
        fc.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}[{out}]")
        cumulative += durs[i] - XFADE
        prev = out
    filtergraph = ";".join(fc)
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", filtergraph,
           "-map", f"[{prev}]", "-r", str(FPS), "-c:v", "libx264",
           "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", OUT]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2500:], file=sys.stderr); sys.exit(1)
    total = sum(durs) - XFADE * (len(durs) - 1)
    print(f"\nOK -> {OUT}  (~{total:.1f}s, {len(pngs)} slides)")


if __name__ == "__main__":
    stitch(render())
