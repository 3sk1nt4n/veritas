#!/usr/bin/env python3
"""Stage 2 of the narrated cut. Reuses build_video.py for the deck, but sets each
slide's duration from its narration length, rebuilds the silent video, computes
each slide's start time on the crossfaded timeline, places that slide's mastered
narration there, and muxes it. Output: docs/veritas-demo-narrated.mp4

Run with system python3 AFTER narr_synth.py has produced video_build/narr/*.
"""
import os, sys, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_video as bv

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(bv.BUILD, "narr")
OUT = os.path.join(HERE, "veritas-demo-narrated.mp4")
SILENT = "/tmp/veritas_silent.mp4"
LEAD, TAIL, FLOOR = 0.45, 0.55, 3.0

dur = json.load(open(os.path.join(WORK, "durations.json")))
assert len(dur) == len(bv.SLIDES), f"{len(dur)} durations vs {len(bv.SLIDES)} slides"

# 1. narration drives each slide's duration
for i, s in enumerate(bv.SLIDES):
    s["dur"] = max(FLOOR, LEAD + dur[str(i)] + TAIL)

# 1b. Crossfades compress the visual timeline while each slide keeps its full
# narration length, so a multi-reveal slide's voiceover can run into the next
# slide's line (two voices at once). Grow offending slides until every pair of
# consecutive narration clips is separated by at least MIN_GAP of clean silence.
# ~1s gives a full beat of breathing room between slides (no rushed back-to-back
# lines) and lets the 1s visual crossfade play out entirely during the pause.
MIN_GAP = 1.0

def _slide_starts():
    f = bv.plan_clips()
    st = [0.0] * len(f)
    run = f[0]["dur"]
    for k in range(1, len(f)):
        e = f[k]["edge"][1]
        st[k] = run - e
        run += f[k]["dur"] - e
    ss = {}
    for idx, c in enumerate(f):
        if c["j"] == 0:
            ss[c["si"]] = st[idx]
    return ss, run

for _ in range(40):
    ss, _tot = _slide_starts()
    changed = False
    for i in range(len(bv.SLIDES) - 1):
        vo_end = ss[i] + LEAD + dur[str(i)]
        nxt_start = ss[i + 1] + LEAD
        gap = nxt_start - vo_end
        if gap < MIN_GAP:
            bv.SLIDES[i]["dur"] += (MIN_GAP - gap) + 0.02
            changed = True
    if not changed:
        break

# 2. plan clips; reuse existing slide PNGs (content unchanged), render only if missing
flat = bv.plan_clips()
need = False
for c in flat:
    c["png"] = os.path.join(bv.BUILD, f"s{c['si']:02d}_{c['j']}.png")
    if not os.path.exists(c["png"]):
        need = True
if need:
    print("rendering slides...")
    bv.render(flat)
else:
    print("reusing existing slide PNGs")

# 3. build the silent video on the narration-driven timeline
bv.OUT = SILENT
bv.stitch(flat)

# 4. compute each clip's start on the crossfaded timeline (same math as stitch)
starts = [0.0] * len(flat)
running = flat[0]["dur"]
for i in range(1, len(flat)):
    edge = flat[i]["edge"][1]
    starts[i] = running - edge
    running += flat[i]["dur"] - edge
total = running
slide_start = {}
for idx, c in enumerate(flat):
    if c["j"] == 0:
        slide_start[c["si"]] = starts[idx]

# 5. place each slide's narration at slide_start + LEAD, mix to one track
ins, fc = [], []
n = len(bv.SLIDES)
for i in range(n):
    vo = os.path.join(WORK, f"slide_vo_{i:02d}.wav")
    assert os.path.exists(vo), f"missing {vo}"
    ins += ["-i", vo]
    ms = max(0, int(round((slide_start[i] + LEAD) * 1000)))
    fc.append(f"[{i}:a]adelay={ms}:all=1[a{i}]")
mix = "".join(f"[a{i}]" for i in range(n)) + \
      f"amix=inputs={n}:duration=longest:normalize=0[m];[m]apad=whole_dur={total:.3f}[out]"
subprocess.run(["ffmpeg", "-y", *ins, "-filter_complex", ";".join(fc) + ";" + mix,
                "-map", "[out]", "-ar", "48000", "/tmp/vo_full.wav"], check=True)
print(f"audio track built ({total:.1f}s)")

# 6. mux narration onto the silent video
subprocess.run(["ffmpeg", "-y", "-i", SILENT, "-i", "/tmp/vo_full.wav",
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                "-b:a", "256k", "-ar", "48000", "-movflags", "+faststart", OUT], check=True)
print(f"NARRATED OK -> {OUT}  (~{total:.1f}s)")
