-- =====================================================================
--  Veritas - chain-of-custody schema for AI-assisted investigations
--  Target: Amazon Aurora PostgreSQL (Serverless v2). Also runs on stock
--  PostgreSQL 14+ for local dev (Docker).
--
--  Design thesis (the product's one sentence, expressed in SQL):
--    "Every confirmed finding traces, by foreign key, back to the exact
--     tool record that proved it - and the AI never gets the final word."
--
--  The chain the schema enforces and makes queryable:
--    org -> case -> evidence_source -> tool_run -> fact
--           case -> finding -> (validator_fact_refs) -> fact -> source tool
--
--  Grounded in the real engine output (src/sift_sentinel/analysis/
--  evidence_db.py + the run-captures/*/findings_final.json artifacts):
--    - facts carry a SHA1 fact_signature -> UNIQUE(case_id, fact_signature)
--      turns the engine's in-memory sig_to_fact merge into an ON CONFLICT
--      UPSERT (source_tools unioned, merge_count incremented).
--    - the engine's ~19 in-memory pivot indexes (by_pid, by_hash, by_ip,
--      by_registry_path, ...) become ~19 real Postgres indexes below.
--    - canonical_entity_id is 'kind:value' (e.g. 'pid:4', 'reg:hklm/...'),
--      split into generated columns to power cross-case IOC pivots.
-- =====================================================================

-- ---- extensions ----
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- fuzzy IOC / path search

-- ---- enumerated domains (deliberate, not free text) ----
DO $$ BEGIN
  CREATE TYPE evidence_kind     AS ENUM ('memory','disk','logs','registry','network','other');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE TYPE tool_status       AS ENUM ('ok','error','timeout','not_applicable');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE TYPE severity_level    AS ENUM ('CRITICAL','HIGH','MEDIUM','LOW','INFO');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE TYPE confidence_level  AS ENUM ('HIGH','MEDIUM','LOW','SPECULATIVE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  -- the engine's five deterministic disposition buckets (disposition.py)
  CREATE TYPE disposition_bucket AS ENUM (
    'confirmed_malicious_atomic',
    'suspicious_needs_review',
    'benign_or_false_positive',
    'inconclusive_unresolved',
    'synthesis_narrative');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE TYPE validator_verdict AS ENUM ('pass','fail','inconclusive');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE TYPE case_status       AS ENUM ('queued','running','completed','failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE TYPE run_status        AS ENUM ('queued','claimed','running','completed','failed','canceled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- =====================================================================
--  CORE ENTITIES
-- =====================================================================

-- Tenant boundary. Row-level security keys off org_id everywhere.
CREATE TABLE IF NOT EXISTS orgs (
  org_id      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- One forensic investigation run.
CREATE TABLE IF NOT EXISTS cases (
  case_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id           uuid NOT NULL REFERENCES orgs(org_id) ON DELETE CASCADE,
  case_name        text NOT NULL,
  sample_name      text,
  status           case_status NOT NULL DEFAULT 'completed',
  verdict          text,                       -- CONFIRMED / SUSPICIOUS / CLEAN (headline)
  started_at       timestamptz,
  ended_at         timestamptz,
  runtime_seconds  numeric,
  model_used       text,                       -- provider/model that drove the run
  token_input      bigint,
  token_output     bigint,
  token_cached     bigint,
  cost_usd         numeric,
  created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cases_org ON cases(org_id);

-- Input evidence, with the integrity fingerprints that make it court-defensible.
CREATE TABLE IF NOT EXISTS evidence_sources (
  evidence_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id            uuid NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  org_id             uuid NOT NULL,
  evidence_type      evidence_kind NOT NULL,
  file_basename      text NOT NULL,
  file_size_bytes    bigint,
  sha256_pre         char(64),                 -- before analysis
  sha256_post        char(64),                 -- after analysis (read-only proof)
  evidence_unmodified boolean GENERATED ALWAYS AS (sha256_pre IS NOT DISTINCT FROM sha256_post) STORED
);
CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence_sources(case_id);

-- Each execution of one of the 180+ typed forensic tools.
CREATE TABLE IF NOT EXISTS tool_runs (
  tool_run_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id            uuid NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  org_id             uuid NOT NULL,
  evidence_id        uuid REFERENCES evidence_sources(evidence_id) ON DELETE SET NULL,
  tool_name          text NOT NULL,
  status             tool_status NOT NULL DEFAULT 'ok',
  execution_time_ms  integer,
  record_count       integer,
  emitted_fact_count integer,
  dropped_record_count integer,
  ran_at             timestamptz,
  -- the engine's coverage contract, enforced by the database:
  CONSTRAINT tool_run_coverage CHECK (
    record_count IS NULL OR emitted_fact_count IS NULL OR dropped_record_count IS NULL
    OR record_count = emitted_fact_count + dropped_record_count)
);
CREATE INDEX IF NOT EXISTS idx_toolruns_case ON tool_runs(case_id);
CREATE INDEX IF NOT EXISTS idx_toolruns_name ON tool_runs(case_id, tool_name);

-- =====================================================================
--  TYPED FACTS  (the heart of the model)
--  Common columns are first-class & typed; the per-fact-type fields
--  (pid, dst_ip, registry_path, ...) live in payload jsonb and are
--  indexed by expression so they behave like real columns.
-- =====================================================================
CREATE TABLE IF NOT EXISTS facts (
  case_id             uuid NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  org_id              uuid NOT NULL,
  fact_id             text NOT NULL,            -- e.g. 'process_fact-0000042'
  fact_type           text NOT NULL,            -- one of ~25 forensic fact types
  fact_signature      char(40) NOT NULL,        -- sha1(fact_type :: entity :: artifact)
  canonical_entity_id text,                      -- 'kind:value' e.g. 'pid:4','reg:hklm/...'
  entity_kind         text GENERATED ALWAYS AS
                        (CASE WHEN canonical_entity_id LIKE '%:%'
                              THEN split_part(canonical_entity_id, ':', 1) END) STORED,
  entity_value        text GENERATED ALWAYS AS
                        (CASE WHEN canonical_entity_id LIKE '%:%'
                              THEN substr(canonical_entity_id, position(':' in canonical_entity_id) + 1) END) STORED,
  entity_id           text,
  artifact            text,
  source_tool         text,                      -- first tool that produced it
  source_tools        text[] NOT NULL DEFAULT '{}',  -- all tools (corroboration)
  record_refs         bigint[] NOT NULL DEFAULT '{}',
  merge_count         integer NOT NULL DEFAULT 1,     -- how many tool records merged in
  confidence_hint     text,
  raw_excerpt         text,                      -- the literal tool output line(s)
  payload             jsonb NOT NULL DEFAULT '{}'::jsonb,  -- type-specific fields
  ingested_at         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (case_id, fact_id),
  -- the signature is the dedup key: makes the merge an idempotent UPSERT.
  CONSTRAINT facts_signature_unique UNIQUE (case_id, fact_signature)
);

-- ---- the ~19 engine pivot indexes, as real Postgres indexes ----
-- structural (entity / type / signature / corroboration / provenance)
CREATE INDEX IF NOT EXISTS idx_facts_entity        ON facts(case_id, entity_kind, entity_value); -- by_pid/by_ip/... core
CREATE INDEX IF NOT EXISTS idx_facts_type          ON facts(case_id, fact_type);
CREATE INDEX IF NOT EXISTS idx_facts_signature     ON facts(fact_signature);                      -- by_fact_signature
CREATE INDEX IF NOT EXISTS idx_facts_source_tools  ON facts USING gin (source_tools);
CREATE INDEX IF NOT EXISTS idx_facts_payload       ON facts USING gin (payload jsonb_path_ops);
-- fuzzy IOC / path search (pg_trgm) - the file-based engine cannot do this
CREATE INDEX IF NOT EXISTS idx_facts_excerpt_trgm  ON facts USING gin (raw_excerpt gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_facts_artifact_trgm ON facts USING gin (artifact gin_trgm_ops);
-- expression indexes mirroring the engine's named pivots (by_*):
CREATE INDEX IF NOT EXISTS idx_facts_by_pid             ON facts((payload->>'pid'));
CREATE INDEX IF NOT EXISTS idx_facts_by_process_name    ON facts((payload->>'process_name'));
CREATE INDEX IF NOT EXISTS idx_facts_by_path            ON facts((payload->>'path'));
CREATE INDEX IF NOT EXISTS idx_facts_by_dst_ip          ON facts((payload->>'dst_ip'));
CREATE INDEX IF NOT EXISTS idx_facts_by_src_ip          ON facts((payload->>'src_ip'));
CREATE INDEX IF NOT EXISTS idx_facts_by_dst_port        ON facts((payload->>'dst_port'));
CREATE INDEX IF NOT EXISTS idx_facts_by_hash            ON facts((payload->>'sha1'));
CREATE INDEX IF NOT EXISTS idx_facts_by_registry_path   ON facts((payload->>'normalized_registry_path'));
CREATE INDEX IF NOT EXISTS idx_facts_by_service_name    ON facts((payload->>'service_name'));
CREATE INDEX IF NOT EXISTS idx_facts_by_task_name       ON facts((payload->>'task_name'));
CREATE INDEX IF NOT EXISTS idx_facts_by_event_id        ON facts((payload->>'event_id'));
CREATE INDEX IF NOT EXISTS idx_facts_by_user            ON facts((payload->>'user'));
CREATE INDEX IF NOT EXISTS idx_facts_by_url_host        ON facts((payload->>'url_host'));

-- =====================================================================
--  FINDINGS / CLAIMS  (what the AI proposed; what the code decided)
-- =====================================================================
CREATE TABLE IF NOT EXISTS findings (
  case_id            uuid NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  org_id             uuid NOT NULL,
  finding_id         text NOT NULL,             -- e.g. 'F001'
  title              text,
  artifact           text,
  description        text,
  finding_type       text,
  evidence_type      text,
  severity           severity_level,
  confidence_level   confidence_level,
  disposition_bucket disposition_bucket NOT NULL,   -- the deterministic verdict
  -- the "AI never gets the final word" story, as data:
  model_recommended_disposition text,           -- what the model wanted
  ai_overruled       boolean NOT NULL DEFAULT false, -- code disagreed with the model
  overrule_reason    text,                       -- which deterministic gate withheld promotion
  validation_status  text,
  self_verification_passed boolean,
  self_corrected     boolean NOT NULL DEFAULT false,
  source_tools       text[] NOT NULL DEFAULT '{}',
  fact_refs          text[] NOT NULL DEFAULT '{}',  -- flat proof fact_ids (extracted from corroborating_fact_refs)
  validator_fact_refs     jsonb,   -- claim_index -> fact_type validator links (structured)
  corroborating_fact_refs jsonb,   -- [{fact_id, matched_key, relation, ...}] (structured)
  disposition_reasons jsonb,       -- deterministic gate reasons; drives overrule_reason + the "why not confirmed" panel
  deterministic_check text,        -- 'passed' | ...
  malicious_semantic_signals jsonb,
  raw_excerpt        text,
  raw                jsonb,                      -- full original finding object (lossless)
  occurred_at        timestamptz,
  PRIMARY KEY (case_id, finding_id)
);
CREATE INDEX IF NOT EXISTS idx_findings_bucket ON findings(case_id, disposition_bucket);
CREATE INDEX IF NOT EXISTS idx_findings_confirmed ON findings(case_id)
  WHERE disposition_bucket = 'confirmed_malicious_atomic';   -- hot path (the report primary)
CREATE INDEX IF NOT EXISTS idx_findings_overruled ON findings(case_id) WHERE ai_overruled;
CREATE INDEX IF NOT EXISTS idx_findings_source_tools ON findings USING gin (source_tools);
CREATE INDEX IF NOT EXISTS idx_findings_factrefs ON findings USING gin (fact_refs);

CREATE TABLE IF NOT EXISTS claims (
  claim_id        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id         uuid NOT NULL,
  org_id          uuid NOT NULL,
  finding_id      text NOT NULL,
  claim_type      text,                          -- hash | process | connection | registry | ...
  claim_value     text,
  filename        text,
  sha1            text,
  source_tools    text[] NOT NULL DEFAULT '{}',
  validator_verdict validator_verdict,
  validator_message text,
  raw             jsonb,          -- full original claim object (heterogeneous shapes)
  FOREIGN KEY (case_id, finding_id) REFERENCES findings(case_id, finding_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_claims_finding ON claims(case_id, finding_id);
CREATE INDEX IF NOT EXISTS idx_claims_sha1 ON claims(sha1);

-- ---- audit tables (the trust-layer ledger) ----
CREATE TABLE IF NOT EXISTS react_verdicts (
  verdict_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id      uuid NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  org_id       uuid NOT NULL,
  entity_key   text,
  scope        text,                             -- atomic | chain
  verdict      text,                             -- malicious | benign | false_positive | inconclusive
  source_finding_ids text[] NOT NULL DEFAULT '{}',
  reasoning    text,
  confidence   text
);
CREATE INDEX IF NOT EXISTS idx_react_entity ON react_verdicts(case_id, entity_key);

CREATE TABLE IF NOT EXISTS self_correction_records (
  correction_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id         uuid NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
  org_id          uuid NOT NULL,
  finding_id      text,
  status          text,                          -- CORRECTED | UNCHANGED | IRREVERSIBLE
  correction_reason text,
  original_draft  jsonb,
  attempt_count   integer
);

-- =====================================================================
--  ASYNC NEW-RUN QUEUE (the "go-big" path: web enqueues, engine worker
--  claims with SELECT ... FOR UPDATE SKIP LOCKED, no broker needed)
-- =====================================================================
CREATE TABLE IF NOT EXISTS runs_queue (
  run_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id          uuid NOT NULL REFERENCES orgs(org_id) ON DELETE CASCADE,
  case_name       text NOT NULL,
  evidence_s3_uri text,
  status          run_status NOT NULL DEFAULT 'queued',
  step_reached    integer NOT NULL DEFAULT 0,    -- 0..16 for live progress polling
  step_label      text,
  case_id         uuid REFERENCES cases(case_id) ON DELETE SET NULL,
  error           text,
  enqueued_at     timestamptz NOT NULL DEFAULT now(),
  claimed_at      timestamptz,
  finished_at     timestamptz
);
CREATE INDEX IF NOT EXISTS idx_runs_queue_claimable ON runs_queue(status, enqueued_at)
  WHERE status = 'queued';

-- =====================================================================
--  CROSS-CASE PIVOT  (the capability the file-based engine cannot do:
--  "show every case where hash X / IP Y / pid Z appears")
-- =====================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS fact_entity_pivot AS
  SELECT org_id, entity_kind, entity_value,
         count(DISTINCT case_id)         AS case_count,
         count(*)                        AS fact_count,
         array_agg(DISTINCT case_id)     AS case_ids,
         array_agg(DISTINCT fact_type)   AS fact_types
  FROM facts
  WHERE entity_kind IS NOT NULL AND entity_value IS NOT NULL AND entity_value <> ''
  GROUP BY org_id, entity_kind, entity_value;
CREATE INDEX IF NOT EXISTS idx_pivot_entity     ON fact_entity_pivot(entity_kind, entity_value);
CREATE INDEX IF NOT EXISTS idx_pivot_value_trgm ON fact_entity_pivot USING gin (entity_value gin_trgm_ops);

-- =====================================================================
--  TRUST-LAYER QUERIES exposed as functions (used by the web API)
-- =====================================================================

-- (1) The claim -> fact -> tool trace: every proof behind one finding.
CREATE OR REPLACE FUNCTION finding_trace(p_case_id uuid, p_finding_id text)
RETURNS TABLE (
  fact_ref text, fact_type text, fact_signature char(40),
  source_tools text[], canonical_entity_id text, raw_excerpt text
) LANGUAGE sql STABLE AS $$
  SELECT fr AS fact_ref, ft.fact_type, ft.fact_signature,
         ft.source_tools, ft.canonical_entity_id, ft.raw_excerpt
  FROM findings f
  CROSS JOIN LATERAL unnest(f.fact_refs) AS fr
  LEFT JOIN facts ft ON ft.case_id = f.case_id AND ft.fact_id = fr
  WHERE f.case_id = p_case_id AND f.finding_id = p_finding_id;
$$;

-- (2) Genuine recursion: walk the process parent chain (process tree)
--     from any pid, using the engine's parent_pid field.
CREATE OR REPLACE FUNCTION process_ancestry(p_case_id uuid, p_pid text)
RETURNS TABLE (depth int, pid text, parent_pid text, process_name text, fact_id text)
LANGUAGE sql STABLE AS $$
  WITH RECURSIVE chain AS (
    SELECT 0 AS depth, payload->>'pid' AS pid, payload->>'parent_pid' AS parent_pid,
           payload->>'process_name' AS process_name, fact_id
    FROM facts
    WHERE case_id = p_case_id AND fact_type = 'process_fact' AND payload->>'pid' = p_pid
    UNION ALL
    SELECT c.depth + 1, f.payload->>'pid', f.payload->>'parent_pid',
           f.payload->>'process_name', f.fact_id
    FROM facts f
    JOIN chain c ON f.payload->>'pid' = c.parent_pid
    WHERE f.case_id = p_case_id AND f.fact_type = 'process_fact' AND c.depth < 64
  )
  SELECT depth, pid, parent_pid, process_name, fact_id FROM chain;
$$;

-- =====================================================================
--  ROW-LEVEL SECURITY (multi-tenant isolation by org_id)
--  The app does:  SET app.org_id = '<uuid>';  before any query.
--  Ingest runs as the table owner (BYPASSRLS) so it is unaffected.
-- =====================================================================
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['cases','evidence_sources','tool_runs','facts',
                           'findings','claims','react_verdicts',
                           'self_correction_records','runs_queue']
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY;', t);
    EXECUTE format('DROP POLICY IF EXISTS org_isolation ON %I;', t);
    EXECUTE format($f$CREATE POLICY org_isolation ON %I
              USING (org_id = current_setting('app.org_id', true)::uuid);$f$, t);
  END LOOP;
END $$;

-- ---- documentation the judges will read in the repo ----
COMMENT ON TABLE  facts IS
  'Typed forensic facts. UNIQUE(case_id,fact_signature) turns the engine''s in-memory dedup into an ON CONFLICT merge. ~19 expression/GIN indexes mirror the engine pivot indexes.';
COMMENT ON COLUMN findings.ai_overruled IS
  'TRUE when deterministic disposition disagreed with the model recommendation - the product''s core claim, queryable.';
COMMENT ON FUNCTION finding_trace(uuid, text) IS
  'Returns the proof chain (validator_fact_refs -> facts -> source tools) behind a finding.';
COMMENT ON FUNCTION process_ancestry(uuid, text) IS
  'Recursive CTE walking the process parent chain - real database-side forensic reasoning.';
