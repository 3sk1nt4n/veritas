#!/usr/bin/env python3
"""Veritas ingest adapter.

Loads one Sentinel Ensemble run capture into the Veritas Postgres schema:
  - finding_disposition_buckets.json  -> the authoritative 5-bucket disposition
  - evidence_db.json                  -> ONLY the facts referenced by findings
                                         (the findings-backed subset, ~hundreds,
                                         streamed; the full ~200k-fact firehose
                                         is never loaded)

It derives the product's headline signal - "the AI never gets the final word" -
from each finding's disposition_reasons: when the model/ReAct verdict wanted
'confirmed_malicious' but the deterministic gates withheld promotion, we mark
ai_overruled = TRUE and record the gate reason.

Idempotent per case_name (deterministic uuid5; existing rows for the case are
replaced). Fact UPSERT uses ON CONFLICT(case_id,fact_signature) so the engine's
in-memory signature merge is reproduced in the database.

Usage:
    python ingest.py <capture_dir> --case-name "rd01 (opus)" [--db URL]
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
from collections import Counter, defaultdict

import ijson
import psycopg
from psycopg.types.json import Jsonb

NS = uuid.NAMESPACE_URL
DEFAULT_DB = os.environ.get("DATABASE_URL", "postgresql://postgres:veritas@localhost:5433/veritas")
BUCKETS = (
    "confirmed_malicious_atomic",
    "suspicious_needs_review",
    "benign_or_false_positive",
    "inconclusive_unresolved",
    "synthesis_narrative",
)
# fact object keys that are common/meta; everything else goes into payload jsonb
META_KEYS = {
    "fact_id", "fact_type", "fact_signature", "canonical_entity_id", "entity_id",
    "artifact", "source_tool", "source_tools", "record_ref", "record_refs",
    "source_record_index", "source_record_indices", "raw_excerpt", "raw_excerpts",
    "merge_count", "confidence_hint",
}


def org_id() -> uuid.UUID:
    return uuid.uuid5(NS, "veritas:org:demo")


def case_id_for(name: str) -> uuid.UUID:
    return uuid.uuid5(NS, f"veritas:case:{name}")


def parse_overrule(reasons):
    """From disposition_reasons, recover what the model/ReAct wanted and which
    deterministic gate(s) blocked promotion."""
    model = None
    gates = []
    for r in reasons or []:
        m = re.search(r"react_verdict=([A-Za-z_]+)", r)
        if m and m.group(1).lower() != "none":
            model = m.group(1)
        low = r.lower()
        if "gate:" in low or "gate=" in low or "ineligible" in low or "=fail" in low:
            gates.append(r)
    return model, gates


def load_json(path):
    import json
    with open(path) as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("capture_dir")
    ap.add_argument("--case-name", required=True)
    ap.add_argument("--sample-name", default=None)
    ap.add_argument("--db", default=DEFAULT_DB)
    args = ap.parse_args()

    cap = args.capture_dir
    buckets_path = os.path.join(cap, "finding_disposition_buckets.json")
    evdb_path = os.path.join(cap, "evidence_db.json")
    for p in (buckets_path, evdb_path):
        if not os.path.exists(p):
            print(f"ERROR: missing {p}", file=sys.stderr)
            return 2

    buckets = load_json(buckets_path)
    oid = org_id()
    cid = case_id_for(args.case_name)
    sample = args.sample_name or os.path.basename(cap.rstrip("/"))

    # ---- gather findings + the fact_ids they reference ----
    findings_rows = []
    claims_rows = []
    needed_fact_ids = set()
    bucket_counts = {b: 0 for b in BUCKETS}

    for bucket, items in buckets.items():
        if bucket not in bucket_counts:
            bucket_counts[bucket] = 0
        for it in items or []:
            bucket_counts[bucket] += 1
            fid = it.get("finding_id")
            reasons = it.get("disposition_reasons") or []
            model, gates = parse_overrule(reasons)
            overruled = bool(model == "confirmed_malicious" and bucket != "confirmed_malicious_atomic")
            corro = it.get("corroborating_fact_refs") or []
            fact_refs = sorted({r["fact_id"] for r in corro
                                if isinstance(r, dict) and r.get("fact_id")})
            needed_fact_ids.update(fact_refs)
            findings_rows.append((
                cid, oid, fid, it.get("title"), it.get("artifact"), it.get("description"),
                it.get("finding_type"), it.get("evidence_type"), it.get("severity"),
                it.get("confidence_level"), bucket, model, overruled,
                ("; ".join(gates) if gates else None),
                it.get("validation_status"), it.get("self_verification_passed"),
                bool(it.get("self_corrected", False)), it.get("source_tools") or [],
                fact_refs,
                Jsonb(it.get("validator_fact_refs")) if it.get("validator_fact_refs") is not None else None,
                Jsonb(corro) if corro else None,
                Jsonb(reasons) if reasons else None,
                it.get("deterministic_check"),
                Jsonb(it.get("malicious_semantic_signals")) if it.get("malicious_semantic_signals") is not None else None,
                it.get("raw_excerpt"), Jsonb(it),
            ))
            for c in it.get("claims") or []:
                claims_rows.append((
                    cid, oid, fid, c.get("type"),
                    (str(c.get("value")) if c.get("value") is not None else None),
                    c.get("filename"), c.get("sha1"),
                    c.get("source_tools") or [], Jsonb(c),
                ))

    print(f"findings: {sum(bucket_counts.values())}  buckets: "
          + " ".join(f"{b}={bucket_counts[b]}" for b in BUCKETS))
    print(f"referenced fact_ids (findings-backed subset): {len(needed_fact_ids)}")

    # ---- stream ONLY the referenced facts out of the 310MB evidence_db.json ----
    by_type = defaultdict(set)
    for fid in needed_fact_ids:
        by_type[fid.rsplit("-", 1)[0]].add(fid)

    fact_rows = []
    tool_counter = Counter()
    print("streaming referenced facts from evidence_db.json ...")
    with open(evdb_path, "rb") as f:
        for ftype, lst in ijson.kvitems(f, "typed_facts"):
            ids = by_type.get(ftype)
            if not ids:
                continue
            for obj in lst:
                fxid = obj.get("fact_id")
                if fxid not in ids:
                    continue
                payload = {k: v for k, v in obj.items() if k not in META_KEYS}
                stools = obj.get("source_tools") or ([obj["source_tool"]] if obj.get("source_tool") else [])
                for t in stools:
                    tool_counter[t] += 1
                rrefs = obj.get("record_refs") or ([obj["record_ref"]] if obj.get("record_ref") is not None else [])
                rrefs = [int(x) for x in rrefs if isinstance(x, (int, float))]
                fact_rows.append((
                    cid, oid, fxid, obj.get("fact_type"), obj.get("fact_signature"),
                    obj.get("canonical_entity_id"), obj.get("entity_id"), obj.get("artifact"),
                    obj.get("source_tool"), stools, rrefs,
                    int(obj.get("merge_count") or 1), obj.get("confidence_hint"),
                    obj.get("raw_excerpt"), Jsonb(payload),
                ))
    print(f"facts extracted: {len(fact_rows)}  (missing: {len(needed_fact_ids) - len(fact_rows)})")

    # ---- write to Postgres ----
    with psycopg.connect(args.db, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO orgs(org_id,name) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    (oid, "Veritas Demo Org"))
        # replace any prior load of this case
        cur.execute("DELETE FROM cases WHERE case_id=%s", (cid,))  # cascades to children
        verdict = ("CONFIRMED" if bucket_counts["confirmed_malicious_atomic"] > 0
                   else "SUSPICIOUS" if bucket_counts["suspicious_needs_review"] > 0
                   else "CLEAN")
        cur.execute(
            """INSERT INTO cases(case_id,org_id,case_name,sample_name,status,verdict)
               VALUES (%s,%s,%s,%s,'completed',%s)""",
            (cid, oid, args.case_name, sample, verdict))

        cur.execute(
            """INSERT INTO evidence_sources(case_id,org_id,evidence_type,file_basename)
               VALUES (%s,%s,'memory',%s)""", (cid, oid, sample))

        cur.executemany(
            """INSERT INTO findings(
                 case_id,org_id,finding_id,title,artifact,description,finding_type,
                 evidence_type,severity,confidence_level,disposition_bucket,
                 model_recommended_disposition,ai_overruled,overrule_reason,
                 validation_status,self_verification_passed,self_corrected,source_tools,
                 fact_refs,validator_fact_refs,corroborating_fact_refs,disposition_reasons,
                 deterministic_check,malicious_semantic_signals,raw_excerpt,raw)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            findings_rows)

        if claims_rows:
            cur.executemany(
                """INSERT INTO claims(case_id,org_id,finding_id,claim_type,claim_value,
                     filename,sha1,source_tools,raw)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""", claims_rows)

        if fact_rows:
            cur.executemany(
                """INSERT INTO facts(
                     case_id,org_id,fact_id,fact_type,fact_signature,canonical_entity_id,
                     entity_id,artifact,source_tool,source_tools,record_refs,merge_count,
                     confidence_hint,raw_excerpt,payload)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (case_id,fact_signature) DO UPDATE SET
                     source_tools = (SELECT array_agg(DISTINCT t)
                                     FROM unnest(facts.source_tools || EXCLUDED.source_tools) t),
                     merge_count  = facts.merge_count + 1""",
                fact_rows)

        # minimal tool_runs derived from fact provenance
        cur.executemany(
            """INSERT INTO tool_runs(case_id,org_id,tool_name,status,emitted_fact_count)
               VALUES (%s,%s,%s,'ok',%s)""",
            [(cid, oid, t, n) for t, n in tool_counter.items()])

        conn.commit()
        cur.execute("REFRESH MATERIALIZED VIEW fact_entity_pivot")
        conn.commit()

        # ---- fidelity gate: ingested bucket counts must match the source ----
        cur.execute(
            """SELECT disposition_bucket, count(*) FROM findings
               WHERE case_id=%s GROUP BY 1""", (cid,))
        db_counts = dict(cur.fetchall())
        ok = True
        for b in BUCKETS:
            want = bucket_counts.get(b, 0)
            got = db_counts.get(b, 0)
            flag = "OK" if want == got else "MISMATCH"
            if want != got:
                ok = False
            print(f"  {b:30s} source={want:3d} db={got:3d}  [{flag}]")
        cur.execute("SELECT count(*) FROM facts WHERE case_id=%s", (cid,))
        print(f"  facts in db: {cur.fetchone()[0]}")
        cur.execute("SELECT count(*) FROM findings WHERE case_id=%s AND ai_overruled", (cid,))
        print(f"  ai_overruled findings: {cur.fetchone()[0]}")

    print("INGEST OK" if ok else "INGEST COMPLETED WITH COUNT MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
