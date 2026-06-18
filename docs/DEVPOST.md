# Veritas - Devpost submission pack (copy-paste)

Everything needed to submit Veritas to **H0: Hack the Zero Stack with Vercel and AWS Databases**.
Deadline: **June 29, 2026, 5:00pm PT**. Track 2 (Monetizable B2B).

---

## Step 1 - YouTube upload

- **Visibility:** Public (the rules say public is "highly preferred"). Unlisted is allowed.
- **Copyright:** audio is AI-synthesized narration (Kokoro), no music, no third-party trademarks beyond AWS/Vercel names you are entitled to use. Clean.
- **Thumbnail:** upload `docs/poster.png`.
- Note: re-uploading a fixed video creates a NEW YouTube link. Paste the new link into Devpost (Step 2.6).

**Title:**
```
Veritas: the AI investigation platform where the AI never gets the final word (Amazon Aurora + Vercel)
```

**Description:**
```
Veritas is the trust layer for AI investigations. An autonomous agent investigates digital evidence end to end, but deterministic code - not the model - decides what is "confirmed," and every finding traces by foreign key to the exact forensic tool that proved it. When the model over-calls a threat, Veritas overrules it and shows the gate that withheld promotion.

AWS database: Amazon Aurora PostgreSQL (Serverless v2) is the system of record. Foreign keys enforce the chain of custody, a UNIQUE fact signature turns cross-tool corroboration into an ON CONFLICT merge, ~19 real indexes (btree, GIN, pg_trgm) power cross-case IOC pivots, a recursive CTE walks the process tree, and a Postgres SELECT ... FOR UPDATE SKIP LOCKED queue drives new investigations. Front end: Next.js 15 on Vercel.

Live app: https://veritas-rouge.vercel.app
Code: https://github.com/3sk1nt4n/veritas

Chapters:
0:00 The AI never gets the final word
0:17 The problem, and who it is for
0:49 The working app, live on Amazon Aurora
2:01 Which AWS database, and how it is used
2:30 Close

Built for H0: Hack the Zero Stack with Vercel and AWS Databases. Track 2 (Monetizable B2B).
I created this video for the purposes of entering the H0 Hackathon. #H0Hackathon
```

**Tags:** `Amazon Aurora, AWS, Vercel, Next.js, PostgreSQL, DFIR, digital forensics, incident response, AI, H0Hackathon`

---

## Step 2 - Devpost form (H01.devpost.com -> Enter a Submission)

**2.1 Project name**
```
Veritas
```

**2.2 Elevator pitch / tagline**
```
AI investigates the evidence, but deterministic code - not the model - has the final word, and every finding traces by foreign key to the tool that proved it. A chain-of-custody platform on Amazon Aurora + Vercel.
```

**2.3 Project Story / description**
```
## Inspiration
High-stakes work is adopting AI fastest - security incident response, fraud, compliance, e-discovery - and that is exactly where you cannot ship a conclusion you cannot audit. An agent that says "this host is compromised" is worthless, or worse, if it occasionally hallucinates and no one can trace the claim back to proof. Today's tools ask analysts to trust the model. Courts, insurers, and auditors do not. Veritas makes the trust provable.

## What it does
An autonomous agent investigates digital evidence end to end, but deterministic code - not the model - decides what is "confirmed," and every finding traces by foreign key to the exact tool record that proved it.
- Case dashboard: verdict, a SHA-256 evidence-integrity badge, and the five-way disposition scoreboard.
- AI-overruled view: where the model wanted CONFIRMED MALICIOUS but the code said SUSPICIOUS, with the exact gate that withheld promotion.
- Proof chain: one click expands a finding into claim -> validated fact -> source forensic tool, with the raw tool output.
- Cross-case IOC pivot: type a hash, IP, or PID and see every case it appears in - one indexed Aurora query across the whole corpus.
- Queue a new investigation: Postgres-as-queue; a worker claims jobs with SELECT ... FOR UPDATE SKIP LOCKED and streams 16-step progress.

The data is real: every case is an actual Windows-intrusion investigation ingested from the open-source Sentinel Ensemble engine. No numbers are invented - the ingest adapter asserts the database counts match the engine output exactly.

## How we built it (Amazon Aurora PostgreSQL Serverless v2)
Aurora is the system of record, and the data model is the product:
- Foreign keys enforce the chain of custody - a finding cannot cite proof that does not exist.
- UNIQUE(case_id, fact_signature) turns the engine's in-memory SHA-1 dedup into an idempotent ON CONFLICT UPSERT - cross-tool corroboration in one statement.
- The engine's ~19 in-memory pivot indexes become ~19 real Postgres indexes (btree, GIN on JSONB, pg_trgm for fuzzy IOC search).
- A recursive CTE walks the process tree; a finding_trace() function returns the full proof chain.
- Row-level security by org_id is scaffolded for multi-tenant SaaS; a materialized view powers the cross-case pivot; Serverless v2 scales to zero between investigations.

Front end: Next.js 15 (App Router) on Vercel, server components querying Aurora directly over SSL, UI accelerated with v0. Async worker: Postgres-as-queue with SKIP LOCKED.

## Challenges we ran into
Keeping the AI honest without making the app a black box: the override had to be a real column, the proof a real join, the corroboration a real merge - so the trust is queryable, not asserted. Modeling ~25 heterogeneous fact types and mirroring the engine's 19 pivot indexes in Postgres without an N+1 read storm drove the schema.

## Accomplishments
A live, public, no-login app on real forensic data where the AI is overruled by code in plain sight, every claim is one query from its proof, and cross-case hunting is a single indexed Aurora query the file-based engine cannot do.

## What's next
Productionize multi-tenant auth on the RLS already scaffolded; stream the worker's 16-step progress over the wire; broaden ingest to multimodal artifacts; and offer the trust layer as an API any AI investigation product can embed.

Built for the H0 Hackathon - Track 2 (Monetizable B2B). #H0Hackathon
```

**2.4 Built With**
```
next.js, typescript, react, tailwindcss, vercel, v0, amazon-aurora, aurora-serverless-v2, postgresql, aws, python
```

**2.5 Try it out links**
```
https://veritas-rouge.vercel.app
https://github.com/3sk1nt4n/veritas
```

**2.6 Video link:** paste the YouTube URL from Step 1.

**2.7 Gallery image / thumbnail:** upload `docs/poster.png`.

**2.8 Hackathon-specific fields**

| Field | Value |
|---|---|
| Track | Track 2 - Monetizable B2B app |
| Which AWS database(s) | Amazon Aurora PostgreSQL (Serverless v2) |
| Architecture diagram | upload `docs/architecture.png` |
| AWS database screenshot | upload `docs/assets/rds.png` |
| Published Vercel project | https://veritas-rouge.vercel.app |
| Vercel Team ID | `team_IJ1d8VVxwWamhI3235A7kyvS` |
| New or existing | New - built entirely during the submission period (June 16-18, 2026) |

---

## Step 3 - Bonus content (free +0.2 to +0.6)

Publish `docs/BLOG.md` (already written, already carries the hackathon disclosure):
1. dev.to is fastest (or Medium / LinkedIn).
2. Paste the full `docs/BLOG.md`.
3. Tags: `aws`, `aurora`, `vercel`, `nextjs`.
4. Keep it public; keep the line "I built this project, Veritas, for the H0 Hackathon. #H0Hackathon".
5. Optionally add the published URL to the Devpost description.

---

## Step 4 - Final pre-submit checklist

- [ ] Live app opens at veritas-rouge.vercel.app with orange colors (latest deploy live)
- [ ] On /runs, queue a job and watch it complete (self-draining fix live)
- [ ] Live dashboard stat row matches the video badge: 3 cases / 2,257 facts / 144 findings / 11 overruled
- [ ] YouTube video is Public and plays
- [ ] Devpost: all fields filled, Team ID pasted, architecture diagram + AWS screenshot attached
- [ ] Click Submit (not just Save draft)
