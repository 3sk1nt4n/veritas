#!/usr/bin/env python3
"""Assemble the FUNCTIONING-FOOTAGE demo cut (footage-first, v2).

Opens ON the live app (continuously-moving intro footage) with the title +
problem narration laid over it, then runs the live app beats (dashboard, the
AI-overrule gate, the proof chain + raw tool output, the cross-case pivot, the
self-draining runs queue), and only THEN the Amazon Aurora explanation cards +
the RDS console + close. No full-screen slide is shown until the app has already
been demonstrated functioning - which is the exact thing the rules require.

Footage from docs/capture_live.py; narration reused from video_build/narr/.
Output: docs/veritas-demo-live.mp4  (<3:00, 1920x1080, H.264 + AAC).

    python3 docs/build_live_cut.py
"""
from __future__ import annotations
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "video_build")
NARR = os.path.join(BUILD, "narr")
NORM = os.path.join(BUILD, "norm")
os.makedirs(NORM, exist_ok=True)
OUT = os.path.join(HERE, "veritas-demo-live.mp4")
SILENT = "/tmp/veritas_live_silent.mp4"
VO_FULL = "/tmp/veritas_live_vo.wav"

W, H, FPS, BG = 1920, 1080, 30, "0x070a10"
LEAD, TAIL, FLOOR, XFADE, MIN_GAP, INTRA_GAP = 0.45, 0.6, 3.0, 0.8, 0.9, 0.55

# segment = (kind, source, vo_index_or_list, trim_seconds_or_None)
# the opener is LIVE app footage carrying the title + problem narration.
SEGMENTS = [
    ("video", "live/beat0_intro.mp4",    [1, 3], None),  # live app + title + the problem
    ("video", "live/beat2_dashboard.mp4",[7],    None),   # verdict + overruled 4x
    ("video", "live/beat3_overrule.mp4", [8],    None),   # AI did not get the final word + gate
    ("video", "live/beat4_proof.mp4",    [9],    None),   # proof chain -> raw tool output
    ("video", "live/beat5_pivot.mp4",    [10],   None),   # cross-case pivot (3 cases)
    ("video", "live/beat6_runs.mp4",     [11],   10.5),   # live self-draining queue
    ("still", "s15_0.png",               [15],   None),   # Amazon Aurora PostgreSQL Serverless v2
    ("still", "s16_6.png",               [16],   None),   # how Aurora is used (FK / ON CONFLICT / CTE)
    ("still", "s17_0.png",               [17],   None),   # the real cluster in the AWS console
    ("still", "s18_0.png",               [18],   None),   # close
]

# RUBRIC variant (RUBRIC=1): same footage-first spine, but signposts the three
# judge questions (problem/for-whom, the working app, which AWS database) with
# the existing "First/Second/Third" narration. Still opens on the live app and
# keeps the app demo as the visual majority. -> docs/veritas-demo-live-v3.mp4
RUBRIC_SEGMENTS = [
    ("video", "live/beat0_intro.mp4",    [1, 2],  None),  # live app + title + "First: what problem, and for whom?"
    ("still", "s03_2.png",               [3],     None),  # the problem (what)
    ("still", "s04_0.png",               [4],     None),  # for whom
    ("still", "s05_0.png",               [5],     None),  # why this problem (high-stakes AI adoption)
    ("video", "live/beat2_dashboard.mp4",[6, 7],  None),  # "Second: the working application, live on Aurora" + verdict/overruled
    ("video", "live/beat3_overrule.mp4", [8],     None),  # AI did not get the final word + gate
    ("video", "live/beat4_proof.mp4",    [9],     None),  # proof chain -> raw tool output
    ("video", "live/beat5_pivot.mp4",    [10],    None),  # cross-case pivot (3 cases)
    ("video", "live/beat6_runs.mp4",     [11],    10.5),  # live self-draining queue
    ("still", "s15_0.png",               [14, 15],None),  # "Third: which AWS database, and how?" + Aurora intro
    ("still", "s16_6.png",               [16],    None),  # how Aurora is used (FK / ON CONFLICT / CTE)
    ("still", "s17_0.png",               [17],    None),  # the real cluster in the AWS console
    ("still", "s18_0.png",               [18],    None),  # close
]


def probe(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", path], capture_output=True, text=True)
    return float(o.stdout.strip())


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(" ".join(cmd[:8]), "...", file=sys.stderr)
        print(r.stderr[-1800:], file=sys.stderr)
        sys.exit(1)
    return r


def src_path(s):
    return s if os.path.isabs(s) else os.path.join(BUILD, s)


def main():
    vo_len = json.load(open(os.path.join(NARR, "durations.json")))
    rubric = bool(os.environ.get("RUBRIC"))
    segs_def = RUBRIC_SEGMENTS if rubric else SEGMENTS
    out_path = os.path.join(HERE, "veritas-demo-live-v3.mp4") if rubric else OUT

    segs = []
    for kind, src, vo, trim in segs_def:
        p = src_path(src)
        assert os.path.exists(p), f"missing {p}"
        vos = vo if isinstance(vo, list) else [vo]
        # total spoken span inside this segment (clips placed back to back + gaps)
        vspan = sum(vo_len[str(v)] for v in vos) + INTRA_GAP * (len(vos) - 1)
        clip = None
        if kind == "video":
            full = probe(p)
            clip = min(full, trim) if trim else full
        need = vspan + LEAD + TAIL
        dur = max(need, FLOOR, clip or 0.0)
        segs.append({"kind": kind, "path": p, "vos": vos, "vspan": vspan,
                     "clip": clip, "dur": dur})

    # grow durations so consecutive narration clips keep >= MIN_GAP of clean
    # silence on the crossfaded timeline (mirrors build_narrated.py).
    def starts():
        st = [0.0] * len(segs)
        run_t = segs[0]["dur"]
        for i in range(1, len(segs)):
            st[i] = run_t - XFADE
            run_t += segs[i]["dur"] - XFADE
        return st, run_t

    for _ in range(60):
        st, total = starts()
        changed = False
        for i in range(len(segs) - 1):
            vo_end = st[i] + LEAD + segs[i]["vspan"]
            nxt = st[i + 1] + LEAD
            if nxt - vo_end < MIN_GAP:
                segs[i]["dur"] += (MIN_GAP - (nxt - vo_end)) + 0.02
                changed = True
        if not changed:
            break
    st, total = starts()

    # ---- pass 1: normalize every segment to an identical 1920x1080@30 clip ----
    pad = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
           f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={BG}")
    norm_files = []
    for i, s in enumerate(segs):
        out = os.path.join(NORM, f"seg{i:02d}.mp4")
        if s["kind"] == "video":
            ext = max(0.0, s["dur"] - s["clip"]) + 1.0
            vf = (f"trim=0:{s['clip']:.3f},setpts=PTS-STARTPTS,{pad},fps={FPS},"
                  f"tpad=stop_mode=clone:stop_duration={ext:.3f},setsar=1,format=yuv420p")
            run(["ffmpeg", "-y", "-i", s["path"], "-vf", vf, "-t", f"{s['dur']:.3f}",
                 "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
                 "-crf", "18", "-pix_fmt", "yuv420p", out])
        else:
            vf = f"{pad},fps={FPS},setsar=1,format=yuv420p"
            run(["ffmpeg", "-y", "-loop", "1", "-t", f"{s['dur']:.3f}", "-i", s["path"],
                 "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-preset", "medium",
                 "-crf", "18", "-pix_fmt", "yuv420p", out])
        norm_files.append(out)
        print(f"seg{i:02d} {s['kind']:5s} dur={s['dur']:5.2f}s  vo={s['vos']}  {os.path.basename(s['path'])}")

    # ---- pass 2: xfade the normalized clips into one silent master ----
    inputs = []
    for f in norm_files:
        inputs += ["-i", f]
    fc = [f"[{i}:v]setsar=1,format=yuv420p[v{i}]" for i in range(len(norm_files))]
    prev, cumulative = "v0", segs[0]["dur"]
    for i in range(1, len(norm_files)):
        offset = cumulative - XFADE
        out = f"x{i}"
        fc.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}[{out}]")
        cumulative += segs[i]["dur"] - XFADE
        prev = out
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{prev}]",
         "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart", SILENT])

    # ---- pass 3: place each narration clip on the timeline, mix, mux ----
    placed = []   # (vo_index, delay_ms)
    for i, s in enumerate(segs):
        off = LEAD
        for v in s["vos"]:
            placed.append((v, max(0, int(round((st[i] + off) * 1000)))))
            off += vo_len[str(v)] + INTRA_GAP
    ins, fc = [], []
    for k, (v, ms) in enumerate(placed):
        ins += ["-i", os.path.join(NARR, f"slide_vo_{v:02d}.wav")]
        fc.append(f"[{k}:a]adelay={ms}:all=1[a{k}]")
    mix = "".join(f"[a{k}]" for k in range(len(placed))) + \
          f"amix=inputs={len(placed)}:duration=longest:normalize=0[m];[m]apad=whole_dur={total:.3f}[out]"
    run(["ffmpeg", "-y", *ins, "-filter_complex", ";".join(fc) + ";" + mix,
         "-map", "[out]", "-ar", "48000", VO_FULL])

    run(["ffmpeg", "-y", "-i", SILENT, "-i", VO_FULL, "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
         "-movflags", "+faststart", out_path])

    print(f"\nOK -> {out_path}")
    print(f"   {total:.1f}s ({total/60:.2f} min), {len(segs)} segments, "
          f"opens on LIVE app footage, {sum(1 for s in segs if s['kind']=='video')} footage beats")


if __name__ == "__main__":
    main()
