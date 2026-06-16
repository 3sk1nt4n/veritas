import { q, q1 } from "./db";

export const BUCKETS = [
  "confirmed_malicious_atomic",
  "suspicious_needs_review",
  "benign_or_false_positive",
  "inconclusive_unresolved",
  "synthesis_narrative",
] as const;
export type Bucket = (typeof BUCKETS)[number];

export const BUCKET_LABEL: Record<string, string> = {
  confirmed_malicious_atomic: "Confirmed",
  suspicious_needs_review: "Suspicious",
  benign_or_false_positive: "Benign / FP",
  inconclusive_unresolved: "Inconclusive",
  synthesis_narrative: "Synthesis",
};

export interface CaseRow {
  case_id: string;
  case_name: string;
  sample_name: string | null;
  verdict: string | null;
  status: string;
  model_used: string | null;
  runtime_seconds: number | null;
  cost_usd: number | null;
  fact_count: number;
  finding_count: number;
  overruled_count: number;
  confirmed_count: number;
}

export async function listCases(): Promise<CaseRow[]> {
  return q<CaseRow>(`
    SELECT c.case_id, c.case_name, c.sample_name, c.verdict, c.status::text,
           c.model_used, c.runtime_seconds, c.cost_usd,
           (SELECT count(*) FROM facts f WHERE f.case_id = c.case_id)::int AS fact_count,
           (SELECT count(*) FROM findings g WHERE g.case_id = c.case_id)::int AS finding_count,
           (SELECT count(*) FROM findings g WHERE g.case_id = c.case_id AND g.ai_overruled)::int AS overruled_count,
           (SELECT count(*) FROM findings g WHERE g.case_id = c.case_id
              AND g.disposition_bucket = 'confirmed_malicious_atomic')::int AS confirmed_count
    FROM cases c
    ORDER BY c.created_at DESC, c.case_name`);
}

export async function getCase(caseId: string): Promise<CaseRow | null> {
  return q1<CaseRow>(`
    SELECT c.case_id, c.case_name, c.sample_name, c.verdict, c.status::text,
           c.model_used, c.runtime_seconds, c.cost_usd,
           (SELECT count(*) FROM facts f WHERE f.case_id = c.case_id)::int AS fact_count,
           (SELECT count(*) FROM findings g WHERE g.case_id = c.case_id)::int AS finding_count,
           (SELECT count(*) FROM findings g WHERE g.case_id = c.case_id AND g.ai_overruled)::int AS overruled_count,
           (SELECT count(*) FROM findings g WHERE g.case_id = c.case_id
              AND g.disposition_bucket = 'confirmed_malicious_atomic')::int AS confirmed_count
    FROM cases c WHERE c.case_id = $1`, [caseId]);
}

export async function getScoreboard(caseId: string): Promise<Record<string, number>> {
  const rows = await q<{ disposition_bucket: string; n: number }>(
    `SELECT disposition_bucket::text, count(*)::int AS n FROM findings
     WHERE case_id = $1 GROUP BY 1`, [caseId]);
  const out: Record<string, number> = {};
  for (const b of BUCKETS) out[b] = 0;
  for (const r of rows) out[r.disposition_bucket] = r.n;
  return out;
}

export interface EvidenceRow {
  file_basename: string; evidence_type: string;
  sha256_pre: string | null; sha256_post: string | null; evidence_unmodified: boolean | null;
}
export async function getEvidence(caseId: string): Promise<EvidenceRow[]> {
  return q<EvidenceRow>(
    `SELECT file_basename, evidence_type::text, sha256_pre, sha256_post, evidence_unmodified
     FROM evidence_sources WHERE case_id = $1`, [caseId]);
}

export interface FindingRow {
  finding_id: string; title: string | null; artifact: string | null;
  severity: string | null; confidence_level: string | null;
  disposition_bucket: string; ai_overruled: boolean;
  model_recommended_disposition: string | null; overrule_reason: string | null;
  source_tools: string[]; proof_count: number;
}
export async function listFindings(caseId: string, bucket?: string): Promise<FindingRow[]> {
  const params: unknown[] = [caseId];
  let where = "case_id = $1";
  if (bucket) { params.push(bucket); where += " AND disposition_bucket = $2"; }
  return q<FindingRow>(`
    SELECT finding_id, title, artifact, severity::text, confidence_level::text,
           disposition_bucket::text, ai_overruled, model_recommended_disposition,
           overrule_reason, source_tools,
           coalesce(array_length(fact_refs, 1), 0) AS proof_count
    FROM findings WHERE ${where}
    ORDER BY (disposition_bucket = 'confirmed_malicious_atomic') DESC,
             ai_overruled DESC, finding_id`, params);
}

export interface FindingDetail extends FindingRow {
  description: string | null; finding_type: string | null; evidence_type: string | null;
  validation_status: string | null; deterministic_check: string | null;
  disposition_reasons: string[] | null;
  fact_refs: string[];
}
export async function getFinding(caseId: string, findingId: string): Promise<FindingDetail | null> {
  return q1<FindingDetail>(`
    SELECT finding_id, title, artifact, description, finding_type, evidence_type,
           severity::text, confidence_level::text, disposition_bucket::text,
           ai_overruled, model_recommended_disposition, overrule_reason,
           validation_status, deterministic_check, disposition_reasons,
           source_tools, fact_refs,
           coalesce(array_length(fact_refs, 1), 0) AS proof_count
    FROM findings WHERE case_id = $1 AND finding_id = $2`, [caseId, findingId]);
}

export interface ClaimRow {
  claim_type: string | null; claim_value: string | null;
  filename: string | null; sha1: string | null; source_tools: string[];
}
export async function getClaims(caseId: string, findingId: string): Promise<ClaimRow[]> {
  return q<ClaimRow>(
    `SELECT claim_type, claim_value, filename, sha1, source_tools
     FROM claims WHERE case_id = $1 AND finding_id = $2`, [caseId, findingId]);
}

export interface TraceRow {
  fact_ref: string; fact_type: string | null; fact_signature: string | null;
  source_tools: string[] | null; canonical_entity_id: string | null; raw_excerpt: string | null;
}
export async function getTrace(caseId: string, findingId: string): Promise<TraceRow[]> {
  return q<TraceRow>(`SELECT * FROM finding_trace($1, $2)`, [caseId, findingId]);
}

export interface OverruleRow {
  finding_id: string; title: string | null; severity: string | null;
  model_recommended_disposition: string | null; disposition_bucket: string;
  overrule_reason: string | null;
}
export async function getOverruled(caseId: string): Promise<OverruleRow[]> {
  return q<OverruleRow>(`
    SELECT finding_id, title, severity::text, model_recommended_disposition,
           disposition_bucket::text, overrule_reason
    FROM findings WHERE case_id = $1 AND ai_overruled ORDER BY finding_id`, [caseId]);
}

export interface PivotRow {
  entity_kind: string; entity_value: string;
  case_count: number; fact_count: number; case_ids: string[];
}
export async function pivotSearch(query: string): Promise<PivotRow[]> {
  const term = query.trim();
  if (!term) {
    return q<PivotRow>(`
      SELECT entity_kind, entity_value, case_count::int, fact_count::int, case_ids
      FROM fact_entity_pivot WHERE case_count > 1
      ORDER BY case_count DESC, fact_count DESC LIMIT 40`);
  }
  return q<PivotRow>(`
    SELECT entity_kind, entity_value, case_count::int, fact_count::int, case_ids
    FROM fact_entity_pivot WHERE entity_value ILIKE $1
    ORDER BY case_count DESC, fact_count DESC LIMIT 60`, [`%${term}%`]);
}

export async function casesByIds(ids: string[]): Promise<{ case_id: string; case_name: string }[]> {
  if (!ids.length) return [];
  return q(`SELECT case_id, case_name FROM cases WHERE case_id = ANY($1)`, [ids]);
}

// portfolio-wide stats for the landing hero
export async function globalStats() {
  return q1<{ cases: number; facts: number; findings: number; overruled: number; tools: number }>(`
    SELECT (SELECT count(*) FROM cases)::int AS cases,
           (SELECT count(*) FROM facts)::int AS facts,
           (SELECT count(*) FROM findings)::int AS findings,
           (SELECT count(*) FROM findings WHERE ai_overruled)::int AS overruled,
           (SELECT count(DISTINCT tool_name) FROM tool_runs)::int AS tools`);
}
