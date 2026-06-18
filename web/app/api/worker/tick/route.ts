import { NextResponse } from "next/server";
import { q } from "@/lib/db";

export const dynamic = "force-dynamic";

// 16-step Sentinel Ensemble pipeline labels (mirror ingest/worker.py STEPS).
const STEPS = [
  "fingerprint evidence", "sha256 pre-hash", "ssdt health check", "bootstrap typed tools",
  "process inventory", "network inventory", "compile evidence DB", "persistence sweep",
  "ensemble analysis", "validate claims vs facts", "ReAct cross-check", "self-correction pass",
  "confidence calibration", "deterministic disposition", "sha256 post-hash", "compose report",
];

// Serverless demo queue-driver. Advances queued/running demo runs against Aurora
// so the Postgres-as-queue self-drains on Vercel alone - no off-Vercel worker has
// to be running just to watch the queue move. It only steps the state machine and
// links a finished demo run to an already-ingested case; the real Sentinel Ensemble
// engine worker (ingest/worker.py) still runs off-Vercel to process actual evidence
// from S3, so evidence never touches the web tier. The client polls this while any
// run is in flight (see RunsLive).
async function tick() {
  // 1. advance every in-flight run by one step (label from the 16-step list)
  await q(
    `UPDATE runs_queue
        SET step_reached = step_reached + 1,
            step_label   = ($1::text[])[LEAST(step_reached + 1, 16)]
      WHERE status = 'running' AND step_reached < 16`,
    [STEPS]
  );

  // 2. complete runs that reached the last step; link to the org's latest case so
  //    "open case ->" lands on a real, fully-ingested investigation
  await q(
    `UPDATE runs_queue rq
        SET status = 'completed', step_reached = 16, step_label = 'done', finished_at = now(),
            case_id = (SELECT c.case_id FROM cases c
                        WHERE c.org_id = rq.org_id
                        ORDER BY c.created_at DESC LIMIT 1)
      WHERE rq.status = 'running' AND rq.step_reached >= 16`
  );

  // 3. claim the oldest queued run (SKIP LOCKED -> concurrent ticks/tabs never
  //    double-claim); it starts advancing on the next tick.
  await q(
    `UPDATE runs_queue SET status = 'running', step_reached = 1, step_label = $1,
            claimed_at = COALESCE(claimed_at, now())
      WHERE run_id = (
        SELECT run_id FROM runs_queue WHERE status = 'queued'
        ORDER BY enqueued_at FOR UPDATE SKIP LOCKED LIMIT 1)`,
    [STEPS[0]]
  );
}

export async function POST() {
  await tick();
  return NextResponse.json({ ok: true });
}

// GET kept so a scheduler (e.g. Vercel Cron) can also drain the queue with no page open.
export async function GET() {
  await tick();
  return NextResponse.json({ ok: true });
}
