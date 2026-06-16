import { q } from "@/lib/db";
import { Crumbs } from "@/components/ui";
import { RunsLive, type Run } from "@/components/RunsLive";

export const dynamic = "force-dynamic";

export default async function RunsPage() {
  const runs = await q<Run>(`
    SELECT run_id, case_name, status::text AS status, step_reached, step_label,
           case_id, error, to_char(enqueued_at, 'HH24:MI:SS') AS at
    FROM runs_queue ORDER BY enqueued_at DESC LIMIT 50`);

  return (
    <div className="space-y-6">
      <Crumbs items={[{ href: "/", label: "Cases" }, { label: "New investigation" }]} />
      <section>
        <h1 className="text-xl font-semibold tracking-tight text-white">Queue a new investigation</h1>
        <p className="mt-1 max-w-2xl text-sm text-haze">
          Submitting enqueues a job in Aurora. An off-Vercel worker claims it with{" "}
          <code className="mono">SELECT … FOR UPDATE SKIP LOCKED</code>, runs the 16-step Sentinel
          Ensemble pipeline, and ingests only deterministically validated facts back into Aurora.
          Evidence never touches the web tier. Progress below updates live.
        </p>
      </section>
      <RunsLive initial={runs} />
    </div>
  );
}
