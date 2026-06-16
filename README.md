# Veritas - the investigation platform where the AI never gets the final word

> H0: Hack the Zero Stack with Vercel v0 and AWS Databases
> Track 2 (Monetizable B2B) - AWS database: **Amazon Aurora PostgreSQL (Serverless v2)**

Veritas turns an autonomous AI security investigation into a **court-defensible,
queryable record**. An AI agent investigates digital evidence end to end, but
**deterministic code - not the model - decides what is "confirmed,"** and every
finding traces, by foreign key, back to the exact tool record that proved it.
When the model over-calls a threat, Veritas overrules it and shows you the gate
that withheld promotion.

The hard problem in high-stakes AI is trust: you cannot ship conclusions you
cannot audit. Veritas is the trust layer - built on a deliberate Aurora data
model that makes the chain of custody a single SQL query.

## Why Aurora PostgreSQL

The domain is a naturally normalized, join-heavy chain:

```
org -> case -> evidence_source -> tool_run -> fact
        case -> finding --(fact_refs)--> fact -> source tool
```

- **Foreign keys enforce chain-of-custody integrity** - the product's core promise.
- **`UNIQUE(case_id, fact_signature)`** turns the engine's in-memory SHA1 fact
  dedup into an idempotent **`ON CONFLICT` UPSERT** (tools unioned, `merge_count++`).
- The engine's ~19 in-memory pivot indexes (by_pid, by_hash, by_ip,
  by_registry_path, ...) become **~19 real Postgres indexes** (btree + GIN +
  `pg_trgm`), so cross-case IOC hunting is one indexed query the file-based
  engine cannot do.
- A **recursive CTE** walks the process tree server-side; a `finding_trace()`
  function returns the full proof chain behind any finding.

See [`db/schema.sql`](db/schema.sql) and the demo queries in
[`db/demo_queries.sql`](db/demo_queries.sql).

## The data is real

Veritas ingests completed runs of the open-source **Sentinel Ensemble** DFIR
engine. No metrics here are invented: the seed cases are real investigations of a
Windows intrusion (PsExec / PWDumpX credential theft). The ingest adapter asserts
that the database disposition counts match the engine's output exactly.

## Local development (no AWS needed to build)

```bash
# 1. Postgres (local stand-in for Aurora)
sudo docker run -d --name veritas-pg -e POSTGRES_PASSWORD=veritas \
  -e POSTGRES_DB=veritas -p 5433:5432 postgres:16

# 2. schema
sudo docker exec -i veritas-pg psql -U postgres -d veritas < db/schema.sql

# 3. ingest a captured run (findings-backed fact subset only)
python -m venv .venv && . .venv/bin/activate && pip install ijson "psycopg[binary]"
DATABASE_URL=postgresql://postgres:veritas@localhost:5433/veritas \
  python ingest/ingest.py <capture_dir> --case-name "rd01 (opus)"

# 4. the queries that are the demo
sudo docker exec -i veritas-pg psql -U postgres -d veritas < db/demo_queries.sql
```

Going to Aurora is a connection-string swap (plus RDS Proxy / Data API for
Vercel's serverless connection pooling).

## Architecture

```
Browser (analyst)
   |
   v
Next.js on Vercel  --reads-->  RDS Proxy / Aurora Data API  -->  Amazon Aurora PostgreSQL (Serverless v2)
   |                                                               cases, evidence_sources, tool_runs,
   | enqueue new run                                               facts (JSONB + ~19 indexes), findings,
   v                                                               claims, audit tables, fact_entity_pivot
runs_queue (Aurora)  <--SELECT FOR UPDATE SKIP LOCKED--  Sentinel Ensemble engine worker (ECS/EC2)
                                                              ^-- reads evidence from Amazon S3
   Trust boundary: raw evidence + raw model output stay engine-side; only
   deterministically validated facts/findings cross into Aurora.
```

## Status

- [x] Aurora schema (deliberate, normalized + JSONB, ~19 indexes, RLS, matview, recursive functions)
- [x] Ingest adapter (real captures -> Postgres, count-fidelity gate, signature merge)
- [x] Trust-layer demo queries (overrule / trace / cross-case pivot / recursion / merge)
- [x] Next.js console on Vercel (dashboard, findings grid, trace-tree hero, IOC pivot, new-run)
- [x] Async new-run worker (Postgres queue + `SELECT FOR UPDATE SKIP LOCKED`) + live progress
- [x] Architecture diagram + submission text + demo script (`docs/`)
- [ ] Aurora deploy + record video + submit — **your steps:** [`docs/YOUR-STEPS.md`](docs/YOUR-STEPS.md)

MIT License. Built on [Sentinel Ensemble](https://github.com/3sk1nt4n/Sentinel-Ensemble).
