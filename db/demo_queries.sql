-- =====================================================================
--  Veritas - the queries that ARE the demo. Each is one SQL statement
--  the file-based engine cannot do; each maps to a screen / on-camera beat.
-- =====================================================================

-- (A) THE HERO: "the AI never gets the final word."
--     Where the model/ReAct wanted CONFIRMED MALICIOUS but the deterministic
--     gates overruled it - with the exact gate that withheld promotion.
\echo '== (A) AI overruled by deterministic code =='
SELECT f.finding_id, f.severity,
       f.model_recommended_disposition AS ai_wanted,
       f.disposition_bucket            AS code_verdict,
       left(f.overrule_reason, 96)     AS withheld_because
FROM findings f JOIN cases c USING (case_id)
WHERE c.case_name = 'rd01 (opus)' AND f.ai_overruled
ORDER BY f.finding_id;

-- (B) THE TRACE: every confirmed finding's proof chain
--     finding -> validator/corroborating fact_refs -> fact -> source tool.
\echo '== (B) claim->fact->tool trace for a confirmed finding =='
SELECT * FROM finding_trace(
  (SELECT case_id FROM cases WHERE case_name = 'rd01 (opus)'), 'F008') LIMIT 8;

-- (C) THE CROSS-CASE PIVOT: one indexed query across every case.
--     "show every entity (hash/ip/pid/registry key) seen in more than one case."
\echo '== (C) cross-case IOC pivot (entity appears in >1 case) =='
SELECT entity_kind, entity_value, case_count, fact_count
FROM fact_entity_pivot
WHERE case_count > 1
ORDER BY case_count DESC, fact_count DESC
LIMIT 10;

-- (D) GENUINE RECURSION: walk the process tree from a pid (server-side).
\echo '== (D) recursive process ancestry from pid 8712 (powershell) =='
SELECT * FROM process_ancestry(
  (SELECT case_id FROM cases WHERE case_name = 'rd01 (opus)'), '8712');

-- (E) SIGNATURE MERGE: facts corroborated by >1 tool (the ON CONFLICT dedup).
\echo '== (E) facts merged across tools (corroboration via fact_signature) =='
SELECT fact_id, array_length(source_tools, 1) AS n_tools, source_tools, merge_count
FROM facts f JOIN cases c USING (case_id)
WHERE c.case_name = 'rd01 (opus)' AND array_length(source_tools, 1) > 1
ORDER BY n_tools DESC
LIMIT 8;

-- (F) DASHBOARD scoreboard: the disposition partition per case.
\echo '== (F) disposition scoreboard =='
SELECT c.case_name, f.disposition_bucket, count(*)
FROM findings f JOIN cases c USING (case_id)
GROUP BY c.case_name, f.disposition_bucket
ORDER BY c.case_name, f.disposition_bucket;
