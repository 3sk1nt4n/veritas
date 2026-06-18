# Veritas - H0 submission text

**Track:** 2 - Monetizable B2B
**AWS Database used:** **Amazon Aurora PostgreSQL (Serverless v2)**
**Front end:** Next.js on Vercel / v0
**Live app:** https://veritas-rouge.vercel.app
**Repo:** https://github.com/3sk1nt4n/veritas

---

## The problem

High-stakes work is adopting AI fastest - security incident response, fraud,
compliance, e-discovery - and that is exactly where you cannot ship a conclusion
you cannot audit. An LLM that says "this host is compromised" is worthless, or
worse, if it occasionally hallucinates and no one can trace the claim to proof.
Today's AI investigation tools ask analysts to trust the model. Courts, insurers,
and auditors do not.

## What Veritas does

Veritas is the trust layer for AI investigations. An autonomous agent
investigates digital evidence end to end - but **deterministic code, not the
model, decides what is "confirmed,"** and **every finding traces by foreign key
to the exact tool record that proved it.** When the model over-calls a threat,
Veritas overrules it and shows the analyst the precise gate that withheld
promotion.

- **Case dashboard** - verdict, evidence-integrity (SHA-256) badge, and the
  five-way disposition scoreboard.
- **The AI-overruled view** - for each finding the model wanted to confirm but
  the code refused, we show "Model proposed: CONFIRMED MALICIOUS → Veritas:
  SUSPICIOUS - promotion withheld" with the failing gate.
- **Proof chain** - one click expands a finding into claim → validated fact →
  source forensic tool, with the raw tool output.
- **Cross-case IOC pivot** - type a hash, IP, or PID and see every case it
  appears in: one indexed Aurora query across the whole corpus.
- **Queue a new investigation** - submit evidence; an off-Vercel worker runs the
  16-step pipeline and ingests only validated facts back into Aurora.

The data is real: every case is an actual investigation of a Windows intrusion,
ingested from the open-source [Sentinel Ensemble](https://github.com/3sk1nt4n/Sentinel-Ensemble)
engine. No numbers are invented - the ingest adapter asserts the database
disposition counts match the engine output exactly.

## Who pays (Track 2: Monetizable B2B)

Veritas is sold to the teams who must defend a verdict: incident-response firms,
in-house security and forensics teams, and cyber-insurers. Pricing is per-analyst
seat plus per-investigation (metered per case ingested), with an enterprise tier
for private deployment, SSO, and the org-scoped row-level security already in the
schema. The unit of value is a court-defensible investigation: a finding that
traces to proof is worth far more than an unauditable AI guess that a court,
insurer, or auditor will throw out. The same trust layer can also be licensed as
an API that any AI investigation product embeds.

## Why Amazon Aurora PostgreSQL - and how it is integrated

The domain is a naturally normalized, join-heavy chain of custody:

```
org → case → evidence_source → tool_run → fact
        case → finding -(fact_refs)→ fact → source tool
```

Aurora is not a checkbox here; the data model is the product:

- **Foreign keys enforce chain-of-custody integrity** - the thing the product
  sells. A finding cannot reference proof that does not exist.
- **`UNIQUE(case_id, fact_signature)`** turns the engine's in-memory SHA1 fact
  dedup into an idempotent **`ON CONFLICT` UPSERT** (source tools unioned,
  `merge_count` incremented) - corroboration across tools, in one statement.
- The engine's **~19 in-memory pivot indexes** (by_pid, by_hash, by_ip,
  by_registry_path, …) become **~19 real Postgres indexes** - btree, GIN on
  JSONB, and `pg_trgm` for fuzzy IOC search - so cross-case hunting is a single
  indexed query the file-based engine cannot do.
- A **recursive CTE** walks the process tree server-side; a `finding_trace()`
  function returns the full proof chain.
- **Row-level security by `org_id`** makes it multi-tenant SaaS-ready; a
  **materialized view** powers the cross-case pivot; **Serverless v2** scales to
  zero between investigations.

DynamoDB was considered and rejected: the 19 pivot indexes would need 5+ GSIs
with multiplying cost, the signature merge needs conditional writes, and the
finding→claims→facts→tool joins are an N+1 read storm. Aurora DSQL was rejected
for the build window (no `pg_trgm`); a single primary region is right for this.

## How we built it

- **Schema** (`db/schema.sql`): deliberate normalized model + JSONB for the ~25
  heterogeneous fact types, with the indexes, RLS, matview, and recursive
  functions above.
- **Ingest** (`ingest/ingest.py`): streams only the findings-backed fact subset
  out of a 310 MB evidence file (hundreds of rows, not 200k), UPSERTs with the
  signature merge, and gates on count-fidelity vs the engine.
- **Web** (`web/`): Next.js 15 App Router, server components querying Aurora
  through a pooled `pg` client over SSL (a direct pooled connection today; RDS
  Proxy / the Data API are a drop-in upgrade behind the same connection string);
  dark investigation-console UI accelerated with v0.
- **Async worker** (`ingest/worker.py`): Postgres-as-queue - claims jobs with
  `SELECT … FOR UPDATE SKIP LOCKED`, runs the pipeline, ingests results.

## What's original

"Deterministic code overrules the AI, and every finding traces to proof" is a
genuinely different posture from every other AI app - and here it is not a
slogan, it is a SQL schema you can query. The overrule is a real column
(`ai_overruled`), the proof is a real foreign key, the corroboration is a real
`ON CONFLICT` merge. The novelty is visible on screen, not asserted in prose.

## What's next

Productionize multi-tenant auth on top of the RLS already scaffolded; stream the
worker's 16-step progress over the wire; broaden ingest to multimodal artifacts;
and offer the trust layer as an API any AI investigation product can call.
