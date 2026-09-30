"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Server } from "lucide-react";
import { getJson } from "@/lib/http";
import { cn, formatDate, formatDuration } from "@/lib/utils";

interface FailedJob {
  id: string;
  video_id: string;
  user_id: string;
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  created_at: string;
}

interface Jobs {
  total: number;
  by_status: Record<string, number>;
  success_rate: number;
  avg_duration_seconds: number | null;
  recent_failures: FailedJob[];
}

const STATUS_STYLES: Record<string, string> = {
  queued: "border-outline-variant/30 text-on-surface-variant",
  running: "border-secondary/30 text-secondary bg-secondary/5",
  completed: "border-emerald-600/30 text-emerald-700 bg-emerald-50",
  failed: "border-error/30 text-error bg-error-container/20",
};

export default function JobsPage() {
  const [jobs, setJobs] = useState<Jobs | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJson<Jobs>("/admin/jobs?failure_limit=25");
      setJobs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 text-red-900 rounded-3xl flex flex-col gap-4 font-literata text-sm max-w-xl">
        <div className="flex items-center gap-2 text-red-700 font-bold">
          <AlertTriangle className="w-5 h-5" />
          <span>Error loading job health</span>
        </div>
        <p>{error}</p>
        <button
          onClick={load}
          className="px-5 py-2 rounded-full bg-red-700 text-white font-semibold self-start hover:bg-red-800 transition"
        >
          Retry
        </button>
      </div>
    );
  }

  if (loading || !jobs) {
    return (
      <div className="flex flex-col gap-6 animate-pulse p-2">
        <div className="h-8 bg-surface-container rounded-lg w-1/3" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 bg-surface-container rounded-2xl" />
          ))}
        </div>
        <div className="h-72 bg-surface-container rounded-3xl" />
      </div>
    );
  }

  const statuses = ["queued", "running", "completed", "failed"];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-8 text-on-surface"
    >
      <div className="flex flex-col">
        <h1 className="font-playfair text-3xl font-bold text-primary">Job health</h1>
        <p className="text-on-surface-variant font-literata text-sm mt-1">
          Analysis queue throughput, reliability and recent failures.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {statuses.map((s) => (
          <div
            key={s}
            className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl p-6 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-on-surface-variant font-medium uppercase tracking-wider">
                {s}
              </span>
              <span
                className={cn(
                  "text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full border capitalize",
                  STATUS_STYLES[s],
                )}
              >
                {s}
              </span>
            </div>
            <div className="font-playfair text-3xl font-extrabold text-primary mt-2">
              {jobs.by_status[s] ?? 0}
            </div>
          </div>
        ))}
      </div>

      <div className="grid sm:grid-cols-3 gap-6">
        <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl p-6 shadow-sm">
          <span className="text-[10px] text-on-surface-variant font-medium uppercase tracking-wider">
            Total jobs
          </span>
          <div className="font-playfair text-2xl font-extrabold text-primary mt-2">
            {jobs.total}
          </div>
        </div>
        <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl p-6 shadow-sm">
          <span className="text-[10px] text-on-surface-variant font-medium uppercase tracking-wider">
            Success rate
          </span>
          <div className="font-playfair text-2xl font-extrabold text-primary mt-2">
            {jobs.success_rate}%
          </div>
        </div>
        <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl p-6 shadow-sm">
          <span className="text-[10px] text-on-surface-variant font-medium uppercase tracking-wider">
            Avg run duration
          </span>
          <div className="font-playfair text-2xl font-extrabold text-primary mt-2">
            {formatDuration(jobs.avg_duration_seconds)}
          </div>
        </div>
      </div>

      <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl shadow-sm overflow-hidden">
        <div className="flex items-center gap-2 px-8 py-5 border-b border-outline-variant/15">
          <Server className="w-4 h-4 text-primary" />
          <h3 className="font-playfair text-lg font-bold text-primary">Recent failures</h3>
        </div>

        {jobs.recent_failures.length === 0 ? (
          <p className="px-8 py-12 text-center font-literata text-sm text-on-surface-variant/60 italic">
            No failed jobs. Everything is healthy.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-outline-variant/15 text-[10px] uppercase tracking-wider text-on-surface-variant font-literata">
                  <th className="px-5 py-3 font-medium">Job</th>
                  <th className="px-5 py-3 font-medium">Attempts</th>
                  <th className="px-5 py-3 font-medium">Error</th>
                  <th className="px-5 py-3 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {jobs.recent_failures.map((f) => (
                  <tr
                    key={f.id}
                    className="border-b border-outline-variant/10 last:border-0 hover:bg-surface-container/30 transition-colors"
                  >
                    <td className="px-5 py-4 font-mono text-[11px] text-on-surface-variant">
                      {f.id.slice(0, 8)}
                    </td>
                    <td className="px-5 py-4 font-literata text-sm text-on-surface-variant">
                      {f.attempts}/{f.max_attempts}
                    </td>
                    <td className="px-5 py-4 font-literata text-xs text-error max-w-md truncate">
                      {f.last_error || "—"}
                    </td>
                    <td className="px-5 py-4 font-literata text-sm text-on-surface-variant">
                      {formatDate(f.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </motion.div>
  );
}
