#!/usr/bin/env python3
"""Veritas async run worker.

The "go-big" path: the web app enqueues a run into the Aurora `runs_queue` table;
this worker claims it with `SELECT ... FOR UPDATE SKIP LOCKED` (no message broker
needed - Postgres IS the queue), drives the 16-step pipeline while writing live
progress, then ingests the validated result into Aurora and marks it completed.

For local/demo runs the 16 steps are simulated and the result is an existing
capture (so the loop is fully demonstrable with no evidence upload, no LLM spend).
In production, replace `simulate_pipeline()` with the real Sentinel Ensemble
engine subprocess that reads evidence from S3 - everything else is unchanged.

    python worker.py --once     # claim & process one job, then exit (for tests)
    python worker.py --loop     # run forever, polling for queued jobs
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

import psycopg

DB = os.environ.get("DATABASE_URL", "postgresql://postgres:veritas@localhost:5433/veritas")
HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURES = "/home/sansforensics/run-captures"
DEFAULT_CAPTURE = "run-rd01-opus-20260611"  # has the full evidence_db.json

STEPS = [
    "fingerprint evidence", "sha256 pre-hash", "ssdt health check", "bootstrap typed tools",
    "process inventory", "network inventory", "compile evidence DB", "persistence sweep",
    "ensemble analysis", "validate claims vs facts", "ReAct cross-check", "self-correction pass",
    "confidence calibration", "deterministic disposition", "sha256 post-hash", "compose report",
]


def claim_one(conn):
    """Atomically claim the oldest queued run. SKIP LOCKED lets many workers run."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE runs_queue SET status = 'claimed', claimed_at = now()
            WHERE run_id = (
                SELECT run_id FROM runs_queue
                WHERE status = 'queued'
                ORDER BY enqueued_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1)
            RETURNING run_id, org_id, case_name, evidence_s3_uri
            """)
        row = cur.fetchone()
    conn.commit()
    return row


def set_step(conn, run_id, i, label, status="running"):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE runs_queue SET status=%s, step_reached=%s, step_label=%s WHERE run_id=%s",
            (status, i, label, run_id))
    conn.commit()


def simulate_pipeline(conn, run_id, delay=0.25):
    for i, label in enumerate(STEPS, start=1):
        set_step(conn, run_id, i, label)
        time.sleep(delay)


def resolve_capture(evidence: str | None) -> str:
    """Map the evidence pointer to a capture dir with a usable evidence_db.json.
    In prod this downloads the real evidence from S3 instead."""
    candidates = []
    if evidence:
        candidates.append(os.path.join(CAPTURES, os.path.basename(evidence)))
    candidates.append(os.path.join(CAPTURES, DEFAULT_CAPTURE))
    for c in candidates:
        if os.path.isdir(c) and os.path.exists(os.path.join(c, "evidence_db.json")):
            return c
    return candidates[-1]


def process(conn, row, delay=0.25) -> bool:
    run_id, org_id, case_name, evidence = row
    print(f"[worker] claimed {run_id}  case={case_name!r}")
    try:
        simulate_pipeline(conn, run_id, delay=delay)
        capture = resolve_capture(evidence)
        env = dict(os.environ, DATABASE_URL=DB)
        res = subprocess.run(
            [sys.executable, os.path.join(HERE, "ingest.py"), capture, "--case-name", case_name],
            capture_output=True, text=True, env=env)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.strip()[-500:] or "ingest failed")
        # link the finished case (deterministic uuid5 used by ingest.py)
        import uuid
        cid = uuid.uuid5(uuid.NAMESPACE_URL, f"veritas:case:{case_name}")
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE runs_queue SET status='completed', step_reached=16, "
                "step_label='done', case_id=%s, finished_at=now() WHERE run_id=%s",
                (str(cid), run_id))
        conn.commit()
        print(f"[worker] completed {run_id} -> case {cid}")
        return True
    except Exception as e:  # noqa: BLE001
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE runs_queue SET status='failed', error=%s, finished_at=now() WHERE run_id=%s",
                (str(e)[:500], run_id))
        conn.commit()
        print(f"[worker] FAILED {run_id}: {e}", file=sys.stderr)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--delay", type=float, default=0.25, help="per-step delay (demo pacing)")
    args = ap.parse_args()

    with psycopg.connect(DB, autocommit=False) as conn:
        if args.once:
            row = claim_one(conn)
            if not row:
                print("[worker] no queued runs")
                return 0
            return 0 if process(conn, row, args.delay) else 1
        # loop
        print("[worker] polling for queued runs (ctrl-c to stop)")
        while True:
            row = claim_one(conn)
            if row:
                process(conn, row, args.delay)
            else:
                time.sleep(1.5)


if __name__ == "__main__":
    sys.exit(main())
