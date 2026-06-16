# I built an AI investigation platform where the AI never gets the final word - on Amazon Aurora + Vercel

*I built this project, Veritas, for the H0: Hack the Zero Stack with Vercel v0 and AWS Databases hackathon. #H0Hackathon*

**Live demo:** https://veritas-rouge.vercel.app · **Code:** https://github.com/3sk1nt4n/veritas

---

## The problem nobody wants to say out loud

High-stakes work is adopting AI fastest: security incident response, fraud,
compliance, e-discovery. And that is exactly where you cannot ship a conclusion
you cannot audit. If an AI says "this machine is compromised" and it is
occasionally hallucinating, that answer is worthless in front of a court, an
insurer, or a regulator.

Most AI tools ask the analyst to trust the model. I wanted to build the opposite:
a system where **deterministic code, not the model, decides what is "confirmed,"
and every finding traces by foreign key back to the exact tool record that proved
it.** When the model over-calls a threat, the system overrules it and shows you
the precise rule that withheld promotion.

That turns out to be, at its heart, a database problem. Which made it a perfect
fit for this hackathon.

## Why this is a database problem (and why Aurora PostgreSQL)

The domain is a naturally normalized chain of custody:

```
org -> case -> evidence_source -> tool_run -> fact
        case -> finding --(fact_refs)--> fact -> source tool
```

I chose **Amazon Aurora PostgreSQL (Serverless v2)** because the data model is
the product, not a storage detail:

- **Foreign keys enforce the chain of custody.** A finding literally cannot
  reference proof that does not exist. That integrity guarantee is the thing the
  product sells.
- **A SHA-1 `fact_signature` as a `UNIQUE` constraint turns corroboration into an
  `ON CONFLICT` UPSERT.** When two different forensic tools observe the same fact,
  the rows merge: the source-tool array is unioned and a `merge_count` is
  incremented. Cross-tool corroboration in one statement.
- **The engine's ~19 in-memory pivot indexes become ~19 real Postgres indexes**
  (btree, GIN over JSONB, and `pg_trgm` for fuzzy IOC search). That makes
  cross-case threat hunting a single indexed query.
- **A recursive CTE walks the process tree server-side**, and a `finding_trace()`
  function returns the full claim -> fact -> tool proof chain.
- **Row-level security by `org_id`** makes it multi-tenant SaaS-ready, a
  **materialized view** powers the cross-case pivot, and **Serverless v2** scales
  down between investigations so a demo costs about a dollar a day.

I genuinely considered DynamoDB and Aurora DSQL. DynamoDB lost because those 19
pivot indexes would need five-plus GSIs with multiplying cost, the signature
merge needs conditional writes, and the finding -> claims -> facts -> tool joins
become an N+1 read storm. DSQL lost only because the build window is short and I
wanted `pg_trgm`. For a join-heavy, integrity-first workload, Aurora PostgreSQL
was the obvious call.

## The build

**Database.** A deliberate normalized schema, with a JSONB column to absorb the
~25 heterogeneous forensic fact types without losing the typed, indexed columns
that matter. The whole thing is one `schema.sql`.

**Ingest.** This was the sharpest lesson. The source engine emits a 310 MB
evidence file per case with around 200,000 facts. Loading all of that would have
been a multi-day fight for zero benefit. Instead the ingest adapter streams the
file and pulls only the few hundred facts that findings actually reference, then
UPSERTs them with the signature merge. A built-in fidelity gate asserts the
database disposition counts match the engine's output exactly, so the data is
provably faithful, not approximated.

**Front end.** Next.js (App Router) on Vercel, with server components querying
Aurora directly through a pooled client. The read screens need zero application
server at request time. I leaned on v0 for the dark "investigation console" look
and hand-built the one screen that is the whole point: the claim -> fact -> tool
trace, with the "the AI proposed X, deterministic code decided Y" reveal.

**Async runs.** For new investigations I used Postgres itself as the queue: the
web app inserts a row, and an off-Vercel worker claims it with
`SELECT ... FOR UPDATE SKIP LOCKED` (no broker), runs the pipeline, and ingests
the validated result. Simple, durable, and one less moving part.

## The moment that makes it click

Open a finding the model wanted to confirm. You see:

> **Model / ReAct proposed:** Confirmed malicious
> **Veritas (deterministic) verdict:** Suspicious - promotion withheld
> *because:* `gate:confirmed_ineligible[rwx_memory_region_uncorroborated, ...]`,
> `MALICIOUS_SEMANTIC_GATE=FAIL`

The AI got overruled, on screen, with the exact reason. Nothing was silently
dropped. And every confirmed finding expands into the real tool output that
proves it. The originality is not a slogan in a pitch deck; it is an
`ai_overruled` column and a foreign key you can query.

## A couple of gotchas, for the next person

- **Vercel runs outside your VPC.** I skipped RDS Proxy and the Data API and used
  a direct connection string with the standard `pg` driver. For a focused app
  that was the lowest-risk path and it just works against a publicly reachable
  Aurora endpoint with SSL.
- **Framework Preset matters.** My first production build failed with "No Output
  Directory named public." The fix was not code: the importer had guessed the
  framework as "Other." Switching the preset to Next.js and redeploying the same
  commit turned it green.

## Result

A live, public, cloud-backed app on Amazon Aurora PostgreSQL Serverless v2 and
Vercel, serving real investigations of a Windows intrusion, where the trust story
is enforced by the schema itself. Three cases, the cross-case IOC pivot working
end to end, and the AI getting overruled by deterministic code, in production.

If you are putting AI anywhere near a high-stakes decision, the lesson generalizes
past forensics: make the trust layer a data model you can query, and let the code,
not the model, get the final word.

*Built for the H0: Hack the Zero Stack with Vercel v0 and AWS Databases hackathon.
#H0Hackathon*
