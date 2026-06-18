#!/usr/bin/env python3
"""Build the Veritas demo video: a motion deck that ANSWERS THE BRIEF beat by beat.

Pipeline: render each slide STATE (HTML -> PNG via chromium), then ffmpeg
crossfades states within a slide (staged reveals) and slides between slides
(varied xfades) into docs/veritas-demo.mp4 (1920x1080, H.264, YouTube-ready).

A slide can declare multiple HTML "states"; non-revealed elements carry class
"reveal" (opacity:0, geometry reserved -> no reflow), so text builds in place.

Drop a real RDS console screenshot at docs/assets/rds.png to auto-embed it.

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
W, H, FPS = 1920, 1080, 30
XFADE = 1.0      # between slides (longer = gentler, premium crossfade)
REVEAL = 0.6     # between states within a slide (softer staged reveals)
STEP = 0.9       # visible time per intermediate reveal state


def data_uri(path: str) -> str:
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden;font-family:'Inter',system-ui,Arial,sans-serif;color:#e6edf6}
body{background:
  radial-gradient(1400px 700px at 82% -10%, rgba(249,115,22,.12), transparent 60%),
  radial-gradient(1000px 600px at 0% 0%, rgba(13,148,136,.10), transparent 55%),
  #070a10;display:flex;flex-direction:column;justify-content:center;padding:0 130px;position:relative}
.mono{font-family:'JetBrains Mono',ui-monospace,monospace}
.reveal{opacity:0}
.kicker{font-size:24px;letter-spacing:5px;text-transform:uppercase;color:#fdba74;margin-bottom:26px;font-weight:600}
.kicker::before{content:"";display:inline-block;width:28px;height:2px;background:#f97316;margin-right:16px;
  vertical-align:middle;box-shadow:0 0 12px #f97316}
.brandmark{position:absolute;top:54px;left:130px;display:flex;align-items:center;gap:14px;color:#8597b3;font-size:22px;letter-spacing:.5px}
.brandmark .b{width:30px;height:30px;border-radius:8px;border:1px solid rgba(249,115,22,.5);background:rgba(249,115,22,.12);
  color:#f97316;display:grid;place-items:center;font-size:18px}
.evbadge{position:absolute;top:60px;right:130px;font-size:15px;letter-spacing:2px;color:#6b7d99;opacity:.65}
.foot{position:absolute;bottom:48px;left:130px;right:130px;display:flex;justify-content:space-between;font-size:19px;color:#6b7d99}
h1.cover{font-size:140px;font-weight:800;letter-spacing:-3px;line-height:.95;
  background:linear-gradient(180deg,#ffffff,#b9cfe6);-webkit-background-clip:text;background-clip:text;color:transparent}
.cover-sub{font-size:42px;color:#aab8cf;margin-top:30px;max-width:1320px;line-height:1.3}
.c{color:#f97316}
h1.cover .c,.big .c{background:linear-gradient(180deg,#fdba74,#f97316);-webkit-background-clip:text;background-clip:text;
  color:transparent;filter:drop-shadow(0 0 30px rgba(249,115,22,.45))}
.thesis{background:linear-gradient(90deg,#2dd4bf,#f97316);-webkit-background-clip:text;background-clip:text;
  color:transparent;filter:drop-shadow(0 0 22px rgba(13,148,136,.38))}
h2{font-size:62px;font-weight:700;letter-spacing:-1px;line-height:1.08;max-width:1480px}
h2::after{content:"";display:block;width:98px;height:4px;margin-top:22px;border-radius:3px;
  background:linear-gradient(90deg,#f97316,rgba(249,115,22,0))}
.big{font-size:88px;font-weight:800;letter-spacing:-2px;line-height:1.04;max-width:1560px;
  background:linear-gradient(180deg,#ffffff,#c4d6ea);-webkit-background-clip:text;background-clip:text;color:transparent}
.sub{font-size:36px;color:#aab8cf;margin-top:34px;max-width:1480px;line-height:1.4}
ul.bul{margin-top:42px;display:flex;flex-direction:column;gap:28px;max-width:1580px}
ul.bul li{list-style:none;display:flex;gap:20px;font-size:31px;color:#cdd8ea;line-height:1.42;letter-spacing:.2px}
ul.bul li::before{content:"";flex:0 0 auto;margin-top:15px;width:12px;height:12px;border-radius:50%;
  background:#f97316;box-shadow:0 0 14px #f97316}
ul.bul b{color:#fff}
.sqlcard{margin-top:30px;border:1px solid #233149;background:#0b0f17;border-radius:14px;padding:22px 28px;
  font-size:22px;line-height:1.55;color:#cdd8ea;max-width:1520px;white-space:pre;
  box-shadow:0 0 0 1px rgba(249,115,22,.08),0 0 50px -16px rgba(249,115,22,.28)}
.sqlcard .kw{color:#fdba74;font-weight:600}
.split{display:flex;gap:70px;align-items:center}
.split .txt{flex:0 0 660px}
.split .txt h2{font-size:54px}
.split .txt h2::after{width:74px;margin-top:18px}
.split .txt .lines{font-size:31px;color:#aab8cf;margin-top:26px;line-height:1.4}
.chips{display:flex;align-items:center;gap:14px;margin-top:34px}
.verdict-chip{display:inline-flex;align-items:center;border-radius:11px;padding:9px 18px;font-weight:700;font-size:25px;border:1px solid}
.vc-confirmed{color:#ef4444;border-color:rgba(239,68,68,.55);background:rgba(239,68,68,.12);filter:drop-shadow(0 0 16px rgba(239,68,68,.25))}
.vc-suspicious{color:#f59e0b;border-color:rgba(245,158,11,.55);background:rgba(245,158,11,.12)}
.vc-arrow{color:#f97316;font-size:30px}
.gate-callout{margin-top:24px;display:inline-flex;align-items:center;gap:12px;border:1px solid rgba(239,68,68,.5);
  background:rgba(239,68,68,.08);color:#fca5a5;border-radius:12px;padding:14px 22px;font-size:23px}
.window{flex:1;border:1px solid #233149;border-radius:16px;overflow:hidden;background:#0b0f17;transition:filter .3s;
  box-shadow:0 40px 90px -30px rgba(0,0,0,.9),0 0 0 1px rgba(249,115,22,.14),0 0 70px -12px rgba(249,115,22,.22)}
.window.dim{filter:brightness(.42) saturate(.85)}
.window .bar{height:54px;display:flex;align-items:center;gap:10px;padding:0 20px;background:#0f1623;border-bottom:1px solid #1e2a40}
.window .bar .dot{width:13px;height:13px;border-radius:50%}
.window .urlpill{margin-left:18px;flex:1;height:32px;border-radius:8px;background:#070a10;border:1px solid #1e2a40;
  display:flex;align-items:center;padding:0 14px;color:#8597b3;font-size:18px}
.window .shotwrap{height:760px;overflow:hidden}
.window img{width:100%;display:block}
.full-img{position:absolute;inset:0;display:grid;place-items:center}
.full-img img{max-width:1660px;max-height:840px;border:1px solid #233149;border-radius:14px;box-shadow:0 40px 90px -30px rgba(0,0,0,.9)}
.vignette{position:absolute;inset:0;pointer-events:none;z-index:1;
  background:radial-gradient(ellipse at 50% 45%, transparent 55%, rgba(7,10,16,.5) 100%)}
.cap{position:absolute;bottom:70px;left:0;right:0;text-align:center;font-size:30px;color:#aab8cf;padding:0 200px}
.proofcard{margin-top:46px;border:1px solid rgba(249,115,22,.35);border-radius:18px;background:rgba(11,30,40,.55);padding:40px 46px;max-width:1520px}
.proofcard .pl{font-size:30px;color:#cdd8ea;line-height:1.5}
.proofcard .pl b{color:#fdba74}
.links{margin-top:40px;font-size:34px;color:#8597b3}
.links .u{color:#fdba74}
.tag-pill{display:inline-block;margin-top:40px;border:1px solid rgba(249,115,22,.4);background:rgba(249,115,22,.1);
  color:#fdba74;border-radius:999px;padding:14px 30px;font-size:30px;font-weight:600}
/* decorative layer */
.grid{position:absolute;inset:0;pointer-events:none;opacity:.6;z-index:0;
  background-image:linear-gradient(rgba(249,115,22,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(249,115,22,.05) 1px,transparent 1px);
  background-size:66px 66px;-webkit-mask-image:radial-gradient(ellipse at 50% 42%, #000 26%, transparent 76%);
  mask-image:radial-gradient(ellipse at 50% 42%, #000 26%, transparent 76%)}
.corner{position:absolute;width:50px;height:50px;border:2px solid rgba(249,115,22,.5);pointer-events:none;z-index:1;box-shadow:0 0 22px -4px rgba(249,115,22,.5)}
.c-tl{top:38px;left:38px;border-right:0;border-bottom:0}
.c-tr{top:38px;right:38px;border-left:0;border-bottom:0}
.c-bl{bottom:38px;left:38px;border-right:0;border-top:0}
.c-br{bottom:38px;right:38px;border-left:0;border-top:0}
.kicker,h1,h2,.big,.sub,.cover-sub,ul.bul,.sqlcard,.split,.proofcard,.links,.tag-pill{position:relative;z-index:2}
.brandmark,.foot,.full-img,.cap,.evbadge{z-index:3}
"""

BRAND = ('<div class="grid"></div>'
         '<div class="corner c-tl"></div><div class="corner c-tr"></div>'
         '<div class="corner c-bl"></div><div class="corner c-br"></div>'
         '<div class="brandmark"><span class="b">&#10003;</span> Veritas</div>')
EVBADGE = '<div class="evbadge mono">3 CASES &middot; 2,257 FACTS &middot; 11 OVERRULED</div>'
HEAD = ('<!doctype html><html><head><meta charset="utf-8">'
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap" rel="stylesheet">'
        f'<style>{CSS}</style></head><body>')
TAIL = "</body></html>"


def _rc(cond):  # reveal class helper
    return "" if cond else ' class="reveal"'


def cover(kicker, title_html, sub):
    foot = '<div class="foot"><span>github.com/3sk1nt4n/veritas</span><span>veritas-rouge.vercel.app</span></div>'
    k = f'<div class="kicker">{kicker}</div>' if kicker else ""
    return f'{BRAND}{k}<h1 class="cover">{title_html}</h1><div class="cover-sub">{sub}</div>{foot}'


def full(img, caption, badge=False):
    b = EVBADGE if badge else ""
    return f'{BRAND}{b}<div class="full-img"><img src="{img}"><div class="vignette"></div></div><div class="cap">{caption}</div>'


def statement(kicker, big_html, sub, reveal=9):
    big = f'<div class="big"{_rc(reveal >= 1)}>{big_html}</div>'
    s = f'<div class="sub"{_rc(reveal >= 2)}>{sub}</div>' if sub else ""
    return f'{BRAND}{EVBADGE}<div class="kicker">{kicker}</div>{big}{s}'


def bullets(title, items, reveal=99, sql=None, sql_shown=False):
    li = "".join(f"<li{_rc(reveal >= i + 1)}><span>{x}</span></li>" for i, x in enumerate(items))
    sqlhtml = f'<div class="sqlcard mono"{_rc(sql_shown)}>{sql}</div>' if sql else ""
    return f'{BRAND}{EVBADGE}<h2>{title}</h2><ul class="bul">{li}</ul>{sqlhtml}'


def shot(kicker, title, lines, url, img):
    return (f'{BRAND}{EVBADGE}<div class="split"><div class="txt"><div class="kicker">{kicker}</div>'
            f'<h2>{title}</h2><div class="lines">{lines}</div></div>'
            f'<div class="window"><div class="bar">'
            f'<span class="dot" style="background:#ff5f57"></span><span class="dot" style="background:#febc2e"></span>'
            f'<span class="dot" style="background:#28c840"></span><span class="urlpill mono">{url}</span></div>'
            f'<div class="shotwrap"><img src="{img}"></div></div></div>')


def hero(reveal, img):
    """Kinetic 3-beat: dim window+text -> lit + verdict chips -> + gate callout."""
    dim = " dim" if reveal < 1 else ""
    chips = (f'<div class="chips"{_rc(reveal >= 1)}>'
             f'<span class="verdict-chip vc-confirmed">CONFIRMED</span>'
             f'<span class="vc-arrow">&rarr;</span>'
             f'<span class="verdict-chip vc-suspicious">SUSPICIOUS</span></div>')
    gate = (f'<div class="gate-callout"{_rc(reveal >= 2)}>'
            f'<span style="color:#ef4444">&#10007;</span> promotion withheld by the exact deterministic gate</div>')
    return (f'{BRAND}{EVBADGE}<div class="split"><div class="txt">'
            f'<div class="kicker">The trust layer</div>'
            f'<h2>The AI proposed CONFIRMED MALICIOUS.<br>The code said SUSPICIOUS.</h2>'
            f'<div class="lines">Nothing is silently dropped.</div>{chips}{gate}</div>'
            f'<div class="window{dim}"><div class="bar">'
            f'<span class="dot" style="background:#ff5f57"></span><span class="dot" style="background:#febc2e"></span>'
            f'<span class="dot" style="background:#28c840"></span><span class="urlpill mono">&hellip;/finding/F001</span></div>'
            f'<div class="shotwrap"><img src="{data_uri(os.path.join(SHOTS, "03-overruled-hero.png"))}"></div></div></div>')


def aurora_proof():
    rds = os.path.join(HERE, "assets", "rds.png")
    if os.path.exists(rds):
        return full(data_uri(rds), "Amazon Aurora PostgreSQL Serverless v2 (us-east-1) - the cluster behind every screen.")
    return (f'{BRAND}<div class="kicker">Real cloud database</div>'
            f'<h2>Amazon Aurora PostgreSQL<br>Serverless v2 &middot; us-east-1</h2>'
            f'<div class="proofcard"><div class="pl">'
            f'Cluster <b>veritas-db</b> &middot; the Vercel front end connects directly, over SSL.<br>'
            f'<b>3</b> real cases &middot; <b>2,257</b> typed facts &middot; <b>144</b> findings &middot; <b>11</b> AI-overruled-by-code.<br>'
            f'Every screen you just saw is a live SQL query against this cluster.</div></div>')


ARCH = data_uri(os.path.join(HERE, "architecture.png"))
STRUCTURE = data_uri(os.path.join(HERE, "structure.png"))
PIPELINE = data_uri(os.path.join(HERE, "pipeline.png"))
SQL = ('<span class="kw">INSERT INTO</span> facts (&hellip;) <span class="kw">VALUES</span> (&hellip;)\n'
       '<span class="kw">ON CONFLICT</span> (case_id, fact_signature) <span class="kw">DO UPDATE</span>\n'
       '  <span class="kw">SET</span> source_tools = array_cat(facts.source_tools, EXCLUDED.source_tools),\n'
       '      merge_count = facts.merge_count + 1;')
AURORA_BULLETS = [
    "<b>Foreign keys enforce the chain of custody</b> - a finding can&rsquo;t cite proof that doesn&rsquo;t exist.",
    "<b>A SHA-1 fact_signature UNIQUE</b> turns cross-tool corroboration into an ON CONFLICT merge.",
    "<b>The engine&rsquo;s ~19 pivot indexes become real Postgres indexes</b> (btree, GIN, pg_trgm).",
    "<b>A recursive CTE</b> walks the process tree; a materialized view powers cross-case pivots.",
    "<b>Aurora Serverless v2 auto-scales ACUs and resumes in seconds</b> - the chain of custody is always live.",
]

# each slide: {dur, states:[html,...], heavy:bool}
SLIDES = [
    # cold open on the pipeline / architecture
    {"dur": 5.5, "heavy": True, "states": [full(ARCH,
            "The system: a Vercel front end, Amazon Aurora as the system of record, an engine worker behind a trust boundary.")]},
    {"dur": 5.0, "states": [cover("H0 &middot; Track 2 (B2B) &middot; Amazon Aurora PostgreSQL + Vercel",
            'VERI<span class="c">TAS</span>',
            'The investigation platform where the AI <span class="thesis">never gets the final word.</span>')]},

    # ---- Q1 ----
    {"dur": 6.0, "states": [statement("Answering the brief &middot; 1 of 3",
            'What problem are we solving, and <span class="c">for whom?</span>', "(and why we chose it)")]},
    {"dur": 8.0, "states": [
        statement("The problem", 'You can&rsquo;t ship an AI conclusion <span class="c">you can&rsquo;t audit.</span>',
                  "An agent can investigate evidence in minutes - but one untraced claim in front of a court kills the verdict, and your credibility with it.", reveal=0),
        statement("The problem", 'You can&rsquo;t ship an AI conclusion <span class="c">you can&rsquo;t audit.</span>',
                  "An agent can investigate evidence in minutes - but one untraced claim in front of a court kills the verdict, and your credibility with it.", reveal=1),
        statement("The problem", 'You can&rsquo;t ship an AI conclusion <span class="c">you can&rsquo;t audit.</span>',
                  "An agent can investigate evidence in minutes - but one untraced claim in front of a court kills the verdict, and your credibility with it.", reveal=2)]},
    {"dur": 7.0, "states": [statement("For whom", 'For the people who must <span class="c">defend</span> the verdict.',
            "SOC analysts, DFIR consultancies, and incident-response insurers: anyone who has to stand behind an AI&rsquo;s conclusion in front of a client, an auditor, or a court.")]},
    {"dur": 7.0, "states": [statement("Why this problem", 'High-stakes work is adopting AI <span class="c">fastest.</span>',
            "And that is exactly where a hallucinated finding is unacceptable. So instead of asking you to trust the model, Veritas makes the trust provable.")]},

    # ---- Q2 ----
    {"dur": 5.0, "states": [statement("Answering the brief &middot; 2 of 3",
            'The <span class="c">working</span> application.', "Live and public, reading real data from Aurora.")]},
    {"dur": 6.0, "heavy": True, "states": [shot("Case dashboard", "Verdict, integrity, disposition.",
            "A SHA-256 &lsquo;evidence unmodified&rsquo; badge - and the headline: the AI was <span class=\"thesis\">overruled 4&times;</span> by deterministic code.",
            "veritas-rouge.vercel.app/case/&hellip;", data_uri(os.path.join(SHOTS, "02-dashboard.png")))]},
    {"dur": 7.5, "heavy": True, "states": [hero(0, None), hero(1, None), hero(2, None)]},
    {"dur": 6.0, "heavy": True, "states": [shot("Proof chain", "Every claim &rarr; validated fact &rarr; source tool.",
            "One finding_trace() query. The raw forensic-tool output is right there.",
            "&hellip;/finding/F008", data_uri(os.path.join(SHOTS, "04-trace.png")))]},
    {"dur": 6.0, "heavy": True, "states": [shot("Cross-case pivot", "One indexed query across every case.",
            "Type a hash, IP, or PID - Aurora returns every case it appears in. The file-based engine cannot.",
            "&hellip;/pivot", data_uri(os.path.join(SHOTS, "05-pivot.png")))]},
    {"dur": 5.5, "heavy": True, "states": [shot("New investigation", "Postgres is the queue.",
            "Enqueue a run; a worker claims it with SELECT FOR UPDATE SKIP LOCKED and streams 16-step progress.",
            "&hellip;/runs", data_uri(os.path.join(SHOTS, "06-runs.png")))]},

    # ---- under the hood: the real engine ----
    {"dur": 5.5, "heavy": True, "states": [full(STRUCTURE,
            "The Veritas repo: a Next.js front end on Vercel, the Amazon Aurora schema, and an async ingest worker.")]},
    {"dur": 7.0, "heavy": True, "states": [full(PIPELINE,
            "End to end: evidence to engine to Aurora to the Vercel app - only validated facts cross the trust boundary.")]},

    # ---- Q3 ----
    {"dur": 5.5, "states": [statement("Answering the brief &middot; 3 of 3",
            'Which <span class="c">AWS database</span>, and how?', "")]},
    {"dur": 7.0, "states": [statement("The AWS database we used",
            'Amazon Aurora PostgreSQL <span class="c">Serverless v2.</span>',
            "Every audit trail is a foreign key. Every proof is a row. <span class=\"thesis\">No hallucination survives the schema.</span>")]},
    {"dur": 11.0, "states": [
        bullets("How Aurora is used", AURORA_BULLETS, reveal=0, sql=SQL, sql_shown=False),
        bullets("How Aurora is used", AURORA_BULLETS, reveal=1, sql=SQL, sql_shown=False),
        bullets("How Aurora is used", AURORA_BULLETS, reveal=2, sql=SQL, sql_shown=False),
        bullets("How Aurora is used", AURORA_BULLETS, reveal=3, sql=SQL, sql_shown=False),
        bullets("How Aurora is used", AURORA_BULLETS, reveal=4, sql=SQL, sql_shown=False),
        bullets("How Aurora is used", AURORA_BULLETS, reveal=5, sql=SQL, sql_shown=False),
        bullets("How Aurora is used", AURORA_BULLETS, reveal=5, sql=SQL, sql_shown=True)]},
    {"dur": 6.5, "heavy": True, "states": [aurora_proof()]},

    # ---- close ----
    {"dur": 6.0, "states": [cover("", 'The AI never gets <span class="thesis">the final word.</span>',
            '<span class="links"><span class="u">veritas-rouge.vercel.app</span> &middot; github.com/3sk1nt4n/veritas</span>'
            '<br><span class="tag-pill">#H0Hackathon</span>')]},
]

# All-gentle set: only soft fades / cross-dissolves / gradient smooth-wipes,
# no hard-edged wipes - reads as one continuous, premium motion.
TRANS = ["fade", "dissolve", "smoothleft", "fade", "dissolve", "smoothright",
         "fade", "dissolve", "smoothleft", "fade", "dissolve", "smoothright",
         "fade", "dissolve", "fade", "dissolve"]


def plan_clips():
    flat, inter = [], 0
    for si, s in enumerate(SLIDES):
        states, D = s["states"], s["dur"]
        n = len(states)
        if n == 1:
            durs = [D]
        else:
            last = max(2.8, D - STEP * (n - 1))
            durs = [STEP] * (n - 1) + [last]
        for j in range(n):
            edge = None
            if not (si == 0 and j == 0):
                if j == 0:
                    edge = (TRANS[inter % len(TRANS)], XFADE); inter += 1
                else:
                    edge = ("fade", REVEAL)
            flat.append({"si": si, "j": j, "dur": durs[j], "heavy": s.get("heavy", False),
                         "edge": edge, "html": states[j]})
    return flat


def render(flat):
    for c in flat:
        hp = os.path.join(BUILD, f"s{c['si']:02d}_{c['j']}.html")
        pp = os.path.join(BUILD, f"s{c['si']:02d}_{c['j']}.png")
        with open(hp, "w") as f:
            f.write(HEAD + c["html"] + TAIL)
        subprocess.run([CHROMIUM, "--headless=new", "--no-sandbox", "--hide-scrollbars",
                        "--force-device-scale-factor=2", f"--window-size={W},{H}",
                        "--virtual-time-budget=5000", "--default-background-color=ff070a10",
                        f"--screenshot={pp}", f"file://{hp}"], capture_output=True)
        if not os.path.exists(pp):
            print(f"FAILED render {pp}", file=sys.stderr); sys.exit(1)
        c["png"] = pp
    print(f"rendered {len(flat)} states across {len(SLIDES)} slides")


def stitch(flat):
    inputs = []
    for c in flat:
        inputs += ["-loop", "1", "-t", f"{c['dur']}", "-i", c["png"]]
    fc = []
    for i, c in enumerate(flat):
        z = "min(zoom+0.00032,1.055)" if c["heavy"] else "min(zoom+0.00020,1.035)"
        # supersample: states are rendered at 2x; keep 2x through zoompan, downscale to 1080p last (crisp text)
        fc.append(f"[{i}:v]scale={W*2}:{H*2}:force_original_aspect_ratio=decrease,"
                  f"pad={W*2}:{H*2}:(ow-iw)/2:(oh-ih)/2:color=0x070a10,setsar=1,fps={FPS},"
                  f"zoompan=z='{z}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W*2}x{H*2},"
                  f"scale={W}:{H}:flags=lanczos,format=yuv420p[v{i}]")
    prev, cumulative = "v0", flat[0]["dur"]
    for i in range(1, len(flat)):
        name, dur = flat[i]["edge"]
        offset = cumulative - dur
        out = f"x{i}"
        fc.append(f"[{prev}][v{i}]xfade=transition={name}:duration={dur}:offset={offset:.3f}[{out}]")
        cumulative += flat[i]["dur"] - dur
        prev = out
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{prev}]",
           "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "17",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-3000:], file=sys.stderr); sys.exit(1)
    print(f"\nOK -> {OUT}  (~{cumulative:.1f}s, {len(flat)} states)")


if __name__ == "__main__":
    flat = plan_clips()
    render(flat)
    stitch(flat)
