# Veritas - demo video script (target 2:45, hard cap 3:00)

> Note: the SHIPPED demo is now `docs/veritas-demo-live.mp4` (2:22, footage-first,
> answers all three judge questions - problem, for whom, why; build the canonical
> cut with `RUBRIC=1`)
> - **real screen-capture footage of the live app functioning**, narrated with
> the same neural voiceover. It is built reproducibly by:
>   1. `python3 docs/capture_live.py`   - drives headless Chromium over the
>      DevTools Protocol against the running app and records each app beat
>      (landing, dashboard, the AI-overrule gate, the proof chain + raw tool
>      output, the cross-case pivot, the self-draining runs queue) to
>      `docs/video_build/live/beat*.mp4`.
>   2. `python3 docs/build_live_cut.py` - interleaves that footage with the
>      title / problem / Aurora / close cards and lays the narration over it.
>
> The earlier `docs/veritas-demo-narrated.mp4` (2:41) was a rendered slide deck
> of static screenshots; it was replaced because the rules require footage that
> shows the project functioning. This file is the narration reference behind both.

Record at 1440-wide, dark room, screen capture + voiceover. Use the live app
(pre-ingested data - never run the slow pipeline on camera). Have these tabs open:
the app, a `psql` window into Aurora, and the AWS Aurora console.

> Lead with the universal problem before any forensic jargon. Judges are AWS
> database experts; give them one real database beat they can love.

---

**0:00-0:20 - The problem (talking head or title card)**
> "High-stakes work is adopting AI fastest - and that's exactly where you can't
> ship a conclusion you can't audit. If an AI says 'this machine is hacked' and
> it's sometimes hallucinating, that's worthless in court. Veritas fixes that:
> the AI investigates, but deterministic code gets the final word, and every
> finding traces to the proof - in Amazon Aurora PostgreSQL."

**0:20-0:40 - Landing + dashboard**
Show the landing (stats: cases, typed facts, **AI overruled by code**). Click a
case.
> "Real investigation of a Windows intrusion. Verdict: CONFIRMED. Evidence
> unmodified, SHA-256 verified. Here's the disposition: 2 confirmed, but look -
> the AI was overruled 4 times by deterministic code."

**0:40-1:15 - THE HERO: AI overruled (the originality beat)**
Open an overruled finding (e.g. F001).
> "The model's ReAct verdict said: confirmed malicious. Veritas said: suspicious -
> promotion withheld. And it tells you exactly why: the RWX memory region was
> uncorroborated, the malicious-semantic gate failed. The AI proposed; the code
> refused; nothing was silently dropped."

**1:15-1:45 - The proof chain (trace)**
Open a confirmed finding (F008, PsExec/PWDumpX). Expand the proof chain.
> "Every confirmed claim links by foreign key to the typed fact that validated
> it, and the forensic tool that produced it - here, the actual amcache and
> appcompatcache records, with the real SHA-1 and path. This whole chain is one
> `finding_trace()` query in Aurora."

**1:45-2:10 - Cross-case pivot (what the file engine can't do)**
Go to Cross-case pivot, type `psexec` (or `8712`).
> "Type any IOC - a hash, an IP, a PID - and Aurora returns every case it appears
> in, instantly. This is one indexed query across the whole corpus. The original
> file-based engine literally cannot do this; the database is what makes it
> possible."

**2:10-2:40 - The database craftsmanship (for the judges)**
Cut to `psql` and the AWS Aurora console. Run two queries from `db/demo_queries.sql`:
1. the `ON CONFLICT` signature merge - show a fact with `merge_count = 2`,
   `source_tools = {vol_psscan, vol_pstree}`.
2. the recursive `process_ancestry()` CTE - powershell → wmiprvse.
> "Under the hood: the SHA-1 fact signature is a UNIQUE constraint, so
> corroboration across tools is an ON CONFLICT merge. The process tree is a
> recursive CTE. Nineteen forensic pivot indexes are real Postgres indexes. This
> is Amazon Aurora PostgreSQL Serverless v2 - here it is in the console."
Show the Aurora resource in the AWS console (the required proof screenshot).

**2:40-2:55 - New run + close**
Show /runs: queue an investigation, watch the 16-step bar move.
> "New evidence is enqueued in Aurora and claimed by a worker with SELECT FOR
> UPDATE SKIP LOCKED - no broker. Veritas: the investigation platform where the
> AI never gets the final word."

---

### Shot checklist (so nothing is missed)
- [ ] AWS Aurora console visible at least once (also captured as the still screenshot)
- [ ] The "AI overruled → here's the gate" moment, full screen
- [ ] The claim→fact→tool expansion with real raw tool output
- [ ] The cross-case pivot returning multiple cases for one entity
- [ ] One live SQL query (ON CONFLICT merge or recursive CTE)
- [ ] Published Vercel URL shown in the address bar
- [ ] Say the words "Amazon Aurora PostgreSQL" out loud at least twice
