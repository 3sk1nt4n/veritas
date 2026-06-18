#!/usr/bin/env python3
"""Stage 1 (Kokoro variant): synthesize per-slide narration with the Kokoro-82M
neural narrator (voice af_heart, the approved 'smooth premium' read) and master
each slide with the approved 'clear + sharp' chain. Run with the tts-venv python.

Drop-in replacement for narr_synth.py: same NARR script, same GAP, same MASTER,
same outputs (docs/video_build/narr/slide_vo_NN.wav @48k + durations.json) so
build_narrated.py consumes it unchanged. No XTTS, no torchaudio monkeypatch -
Kokoro returns numpy/torch audio at 24 kHz which we write directly.

Env:
  VOICE  override the Kokoro voice (default af_heart)
  SPEED  narration speed multiplier (default 1.0; raise to shorten total)
  RERENDER  comma list of slide indices to re-render only (reuses durations.json)
"""
import os, subprocess, json
import numpy as np
import soundfile as sf
from kokoro import KPipeline

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "video_build", "narr"); os.makedirs(WORK, exist_ok=True)
VOICE = os.environ.get("VOICE", "af_heart")
SPEED = float(os.environ.get("SPEED", "1.0"))
LANG = "b" if VOICE.startswith("b") else "a"   # b* = British, a* = American
SR = 24000
GAP = 0.30
MASTER = ("aresample=48000:resampler=soxr,highpass=f=85,afftdn=nf=-20,deesser=i=0.35:f=0.18,"
          "equalizer=f=250:t=q:w=1.0:g=-3,equalizer=f=3000:t=q:w=1.8:g=3.5,equalizer=f=5500:t=q:w=2.2:g=3,"
          "treble=g=3.5:f=7500,aexciter=amount=2.4:freq=7000,"
          "acompressor=threshold=-18dB:ratio=3:attack=12:release=160:makeup=4,alimiter=limit=0.9,"
          "loudnorm=I=-14:TP=-1.5:LRA=11")

# per-slide narration (aligned to build_video.py SLIDES order); each = sentence chunks
NARR = [
  ["Veritas. A Vercel front end, Amazon Aurora as the system of record, and an engine worker behind a trust boundary."],
  ["Veritas.", "The investigation platform where the A.I. never gets the final word."],
  ["First. What problem are we solving, and for whom?"],
  ["You can't ship an A.I. conclusion you can't audit.", "One untraced claim in front of a court kills the verdict, and your credibility with it."],
  ["It is for the people who must defend that verdict.", "Security analysts, incident response firms, and insurers."],
  ["High stakes work is adopting A.I. fastest, exactly where a hallucination is unacceptable, so we made the trust provable."],
  ["Second. The working application, live on Aurora."],
  ["Each case opens with a verdict, an evidence integrity check, and the disposition.", "Here, the A.I. was overruled four times by deterministic code."],
  ["This is the heart of it.", "The model proposed confirmed malicious.", "The code said suspicious, and shows the exact gate that withheld promotion."],
  ["Every claim traces to the validated fact, and the forensic tool that produced it.", "One query, the full proof chain."],
  ["Type any indicator, a hash, an address, a process I.D., and Aurora returns every case it appears in.", "The file based engine cannot do this."],
  ["New evidence is queued in Aurora, and claimed by a worker, with no message broker."],
  ["Under the hood, the project is three tiers.", "A Vercel front end, the Aurora schema, and an async worker."],
  ["End to end, evidence flows through the engine, and only validated facts cross the trust boundary into Aurora."],
  ["Third. Which A.W.S. database, and how?"],
  ["Amazon Aurora PostgreSQL, Serverless v2.", "Every audit trail is a foreign key.", "Every proof is a row."],
  ["Foreign keys enforce the chain of custody.", "A signature constraint merges corroboration across tools, and a recursive query walks the process tree."],
  ["This is the real cluster, in the A.W.S. console.", "Every screen you just saw is a live query against it."],
  ["Veritas.", "The A.I. never gets the final word."],
]


def dur(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", path], capture_output=True, text=True)
    return float(o.stdout.strip())


def synth_chunk(pipeline, text, out_raw):
    parts = []
    for r in pipeline(text, voice=VOICE, speed=SPEED):
        a = getattr(r, "audio", None)
        if a is None:                      # older tuple API fallback
            a = r[2]
        if hasattr(a, "detach"):
            a = a.detach().cpu().numpy()
        parts.append(np.asarray(a, dtype="float32").reshape(-1))
    audio = np.concatenate(parts) if len(parts) > 1 else parts[0]
    sf.write(out_raw, audio, SR)


def master(chunks, out):
    if len(chunks) == 1:
        cmd = ["ffmpeg", "-y", "-i", chunks[0], "-af", MASTER, "-ar", "48000", out]
    else:
        ins = []
        for c in chunks:
            ins += ["-i", c]
        ins += ["-f", "lavfi", "-t", str(GAP), "-i", "anullsrc=r=24000:cl=mono"]
        sidx = len(chunks); nsil = len(chunks) - 1
        fc = f"[{sidx}:a]asplit={nsil}" + "".join(f"[z{j}]" for j in range(nsil)) + ";"
        order = ""
        for j in range(len(chunks)):
            order += f"[{j}:a]"
            if j < nsil:
                order += f"[z{j}]"
        n = len(chunks) + nsil
        fc += order + f"concat=n={n}:v=0:a=1[cc];[cc]{MASTER}[out]"
        cmd = ["ffmpeg", "-y", *ins, "-filter_complex", fc, "-map", "[out]", "-ar", "48000", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("MASTER FAIL:", r.stderr[-900:]); raise SystemExit(1)


DURPATH = os.path.join(WORK, "durations.json")
_only = os.environ.get("RERENDER")
ONLY = set(int(x) for x in _only.split(",")) if _only else None
durations = json.load(open(DURPATH)) if (ONLY and os.path.exists(DURPATH)) else {}
print(f"loading Kokoro-82M (voice={VOICE}, lang={LANG}, speed={SPEED})...")
pipeline = KPipeline(lang_code=LANG)
for i, chunks in enumerate(NARR):
    if ONLY is not None and i not in ONLY:
        continue
    cfiles = []
    for j, txt in enumerate(chunks):
        f = os.path.join(WORK, f"s{i:02d}_c{j}.wav")
        synth_chunk(pipeline, txt, f)
        cfiles.append(f)
    out = os.path.join(WORK, f"slide_vo_{i:02d}.wav")
    master(cfiles, out)
    durations[str(i)] = dur(out)
    print(f"slide {i:02d}: {durations[str(i)]:.2f}s ({len(chunks)} chunks)")
json.dump(durations, open(DURPATH, "w"))
print("SYNTH+MASTER DONE")
