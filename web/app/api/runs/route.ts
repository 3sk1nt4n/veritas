import { NextRequest, NextResponse } from "next/server";
import { q, q1 } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const runs = await q(`
    SELECT run_id, case_name, status::text AS status, step_reached, step_label,
           case_id, error, to_char(enqueued_at, 'HH24:MI:SS') AS at
    FROM runs_queue ORDER BY enqueued_at DESC LIMIT 50`);
  return NextResponse.json({ runs });
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({} as Record<string, unknown>));
  const caseName = String(body.case_name ?? "").trim() || "ad-hoc investigation";
  const evidence = String(body.evidence ?? "").trim() || null;
  const org = await q1<{ org_id: string }>(`SELECT org_id FROM orgs ORDER BY created_at LIMIT 1`);
  if (!org) return NextResponse.json({ error: "no org provisioned" }, { status: 400 });
  const row = await q1<{ run_id: string }>(
    `INSERT INTO runs_queue(org_id, case_name, evidence_s3_uri, status)
     VALUES ($1, $2, $3, 'queued') RETURNING run_id`,
    [org.org_id, caseName, evidence]
  );
  return NextResponse.json({ run_id: row?.run_id });
}
