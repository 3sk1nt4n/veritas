"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

const N_STEPS = 16;

export interface Run {
  run_id: string;
  case_name: string;
  status: string;
  step_reached: number;
  step_label: string | null;
  case_id: string | null;
  error: string | null;
  at: string;
}

const STATUS_TONE: Record<string, string> = {
  queued: "text-haze",
  claimed: "text-brand",
  running: "text-brand-glow",
  completed: "text-benign",
  failed: "text-confirmed",
  canceled: "text-inconclusive",
};

export function RunsLive({ initial }: { initial: Run[] }) {
  const [runs, setRuns] = useState<Run[]>(initial);
  const [name, setName] = useState("");
  const [evidence, setEvidence] = useState("run-rd01-final");
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch("/api/runs", { cache: "no-store" });
      const j = await r.json();
      setRuns(j.runs ?? []);
    } catch { /* ignore transient */ }
  }, []);

  useEffect(() => {
    const id = setInterval(refresh, 1500);
    return () => clearInterval(id);
  }, [refresh]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    await fetch("/api/runs", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ case_name: name || undefined, evidence }),
    });
    setName("");
    setBusy(false);
    refresh();
  }

  return (
    <div className="space-y-6">
      <form onSubmit={submit} className="panel flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
        <label className="flex-1 text-sm">
          <span className="mb-1 block text-xs uppercase tracking-wide text-haze">Case name</span>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. acme-dc01 triage"
            className="w-full rounded-lg border border-line bg-ink-900 px-3 py-2 text-sm text-white outline-none placeholder:text-haze/60 focus:border-brand/50" />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs uppercase tracking-wide text-haze">Evidence source</span>
          <select value={evidence} onChange={(e) => setEvidence(e.target.value)}
            className="rounded-lg border border-line bg-ink-900 px-3 py-2 text-sm text-white outline-none focus:border-brand/50">
            <option value="run-rd01-opus-20260611">memory.raw (rd01)</option>
            <option value="run-rd01-golden-20260611">disk.E01 (rd01 golden)</option>
            <option value="run-rd01-rerun-20260611">triage.zip (rd01 rerun)</option>
          </select>
        </label>
        <button disabled={busy}
          className="rounded-lg border border-brand/40 bg-brand/10 px-4 py-2 text-sm font-medium text-brand-glow transition hover:bg-brand/20 disabled:opacity-50">
          {busy ? "Queueing…" : "Queue investigation"}
        </button>
      </form>

      <div className="space-y-2.5">
        {runs.length === 0 && (
          <div className="panel p-5 text-sm text-haze">No runs yet. Queue one above - a worker will claim it.</div>
        )}
        {runs.map((r) => {
          const pct = Math.round((Math.min(r.step_reached, N_STEPS) / N_STEPS) * 100);
          const done = r.status === "completed";
          const failed = r.status === "failed";
          return (
            <div key={r.run_id} className="panel p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <span className="text-sm text-white">{r.case_name}</span>
                  <span className="ml-2 text-xs text-haze mono">{r.at}</span>
                </div>
                <span className={`text-xs font-medium uppercase tracking-wide ${STATUS_TONE[r.status] ?? "text-haze"}`}>
                  {r.status}
                </span>
              </div>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-ink-800">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${failed ? "bg-confirmed" : done ? "bg-benign" : "bg-brand"}`}
                  style={{ width: `${failed ? 100 : pct}%` }}
                />
              </div>
              <div className="mt-2 flex items-center justify-between text-xs text-haze">
                <span className="mono">
                  {failed ? r.error : `step ${Math.min(r.step_reached, N_STEPS)}/${N_STEPS}` + (r.step_label ? ` · ${r.step_label}` : "")}
                </span>
                {done && r.case_id && (
                  <Link href={`/case/${r.case_id}`} className="text-brand link-ghost hover:!text-brand-glow">
                    open case →
                  </Link>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
