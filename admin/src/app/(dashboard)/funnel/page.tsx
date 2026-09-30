"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowRight } from "lucide-react";
import { getJson } from "@/lib/http";
import { formatNumber } from "@/lib/utils";

interface FunnelStep {
  key: string;
  label: string;
  count: number;
  conversion_from_previous: number | null;
  conversion_from_start: number;
}

export default function FunnelPage() {
  const [steps, setSteps] = useState<FunnelStep[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJson<{ steps: FunnelStep[] }>("/admin/funnel");
      setSteps(data.steps);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load funnel.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex flex-col gap-6 animate-pulse p-2">
        <div className="h-8 bg-surface-container rounded-lg w-1/3" />
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-20 bg-surface-container rounded-2xl" />
        ))}
      </div>
    );
  }

  if (error || !steps) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 text-red-900 rounded-3xl flex flex-col gap-4 font-literata text-sm max-w-xl">
        <div className="flex items-center gap-2 text-red-700 font-bold">
          <AlertTriangle className="w-5 h-5" />
          <span>Error loading funnel</span>
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

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-8 text-on-surface"
    >
      <div className="flex flex-col">
        <h1 className="font-playfair text-3xl font-bold text-primary">Activation funnel</h1>
        <p className="text-on-surface-variant font-literata text-sm mt-1">
          How far creators get from sign-up to generated insights.
        </p>
      </div>

      <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col gap-5">
        {steps.map((step, idx) => (
          <div key={step.key} className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-surface-container flex items-center justify-center text-[11px] font-literata font-semibold text-primary">
                  {idx + 1}
                </span>
                <span className="font-literata text-sm font-medium text-primary">
                  {step.label}
                </span>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-playfair text-lg font-bold text-primary">
                  {formatNumber(step.count)}
                </span>
                <span className="text-[11px] w-14 text-right font-literata text-on-surface-variant">
                  {step.conversion_from_start}%
                </span>
              </div>
            </div>

            <div className="h-3 w-full bg-surface-container rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${Math.min(100, step.conversion_from_start)}%` }}
              />
            </div>

            {step.conversion_from_previous !== null && (
              <div className="flex items-center gap-1.5 text-[10px] text-on-surface-variant font-literata pl-9">
                <ArrowRight className="w-3 h-3" />
                <span>
                  {step.conversion_from_previous}% continued from the previous step
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      <p className="text-[11px] text-on-surface-variant font-literata">
        Note: true day-over-day retention and cohort analysis require an event log,
        which is not yet instrumented — this funnel reflects cumulative totals to date.
      </p>
    </motion.div>
  );
}
