# Veritas

### The investigation platform where the AI never gets the final word.

[![Live demo](https://img.shields.io/badge/Live%20demo-veritas--rouge.vercel.app-22d3ee?style=for-the-badge)](https://veritas-rouge.vercel.app)
[![AWS](https://img.shields.io/badge/Amazon%20Aurora-PostgreSQL%20Serverless%20v2-ff9d3d?style=for-the-badge)](https://aws.amazon.com/rds/aurora/)
[![Vercel](https://img.shields.io/badge/Front%20end-Next.js%20on%20Vercel-ff4d8d?style=for-the-badge)](https://vercel.com)
[![License](https://img.shields.io/badge/License-MIT-e879f9?style=for-the-badge)](LICENSE)

> **H0: Hack the Zero Stack with Vercel v0 and AWS Databases** - Track 2 (Monetizable B2B)
> AWS database: **Amazon Aurora PostgreSQL (Serverless v2)** - Front end: **Next.js on Vercel**

Veritas turns an autonomous AI security investigation into a court-defensible, queryable record.
An agent investigates digital evidence end to end, but **deterministic code, not the model, decides
what is "confirmed,"** and **every finding traces by foreign key to the exact tool record that proved
it.** When the model over-calls a threat, Veritas overrules it and shows the gate that withheld promotion.

**Live, public, no login: https://veritas-rouge.vercel.app**

---

## Architecture

![Veritas architecture](docs/architecture.png)

## End-to-end pipeline

![Veritas pipeline](docs/pipeline.png)

## Project structure

![Veritas project structure](docs/structure.png)

---

## Why Amazon Aurora PostgreSQL

The domain is a naturally normalized, join-heavy chain of custody, and the data model is the product:

- **Foreign keys enforce chain-of-custody integrity** - a finding cannot reference proof that does not exist.
- **`UNIQUE(case_id, fact_signature)`** turns the engine's in-memory SHA1 dedup into an idempotent
  **`ON CONFLICT` UPSERT** - cross-tool corroboration merges in one statement.
- The engine's **~19 pivot indexes become real Postgres indexes** (btree, GIN on JSONB, `pg_trgm` for
  fuzzy IOC search), so cross-case hunting is one indexed query the file-based engine cannot do.
- A **recursive CTE** walks the process tree; a `finding_trace()` function returns the full proof chain.
- **Row-level security by `org_id`** makes it multi-tenant SaaS-ready; a **materialized view** powers the
  cross-case pivot; **Serverless v2** scales down between investigations.

DynamoDB was considered and rejected (19 pivot indexes would need 5+ GSIs, conditional-write merges, and an
N+1 join storm). Aurora DSQL was rejected for the build window (no `pg_trgm`). See [`db/schema.sql`](db/schema.sql)
and [`db/demo_queries.sql`](db/demo_queries.sql).

## The data is real

Every case is an actual investigation of a Windows intrusion, ingested from the open-source
[Sentinel Ensemble](https://github.com/3sk1nt4n/Sentinel-Ensemble) engine. No numbers are invented: the
ingest adapter asserts the database disposition counts match the engine output exactly.

## Run it locally (no AWS needed to build)

```bash
# 1. Postgres (local stand-in for Aurora)
sudo docker run -d --name veritas-pg -e POSTGRES_PASSWORD=veritas \
  -e POSTGRES_DB=veritas -p 5433:5432 postgres:16

# 2. schema + ingest a captured run
sudo docker exec -i veritas-pg psql -U postgres -d veritas < db/schema.sql
python -m venv .venv && . .venv/bin/activate && pip install ijson "psycopg[binary]"
DATABASE_URL=postgresql://postgres:veritas@localhost:5433/veritas \
  python ingest/ingest.py <capture_dir> --case-name "rd01 (opus)"

# 3. the web app
cd web && npm install && DATABASE_URL=postgresql://postgres:veritas@localhost:5433/veritas npm run dev
```

Going to Aurora is a connection-string swap (`DATABASE_URL` + `PGSSL=require`).

## Submission

- **Live app:** https://veritas-rouge.vercel.app
- **Demo video:** [`docs/veritas-demo.mp4`](docs/veritas-demo.mp4) (YouTube link at submission)
- **Submission text:** [`docs/SUBMISSION.md`](docs/SUBMISSION.md)
- **Architecture / pipeline / structure:** [`docs/`](docs/)

MIT License. Built on [Sentinel Ensemble](https://github.com/3sk1nt4n/Sentinel-Ensemble).
