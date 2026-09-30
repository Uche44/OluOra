"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";
import { getJson } from "@/lib/http";
import { cn, formatNumber } from "@/lib/utils";
import { BarChart } from "@/components/charts/BarChart";

interface EndpointUsage {
  endpoint: string;
  units: number;
}

interface TopConsumer {
  user_id: string;
  email: string;
  units: number;
}

interface UsagePoint {
  date: string;
  units: number;
}

interface Usage {
  days: number;
  units_today: number;
  units_window: number;
  by_endpoint: EndpointUsage[];
  series: UsagePoint[];
  top_consumers: TopConsumer[];
}

const RANGES = [7, 30];

export default function UsagePage() {
  const [days, setDays] = useState(7);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJson<Usage>(`/admin/usage?days=${days}`);
      setUsage(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load usage.");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 text-red-900 rounded-3xl flex flex-col gap-4 font-literata text-sm max-w-xl">
        <div className="flex items-center gap-2 text-red-700 font-bold">
          <AlertTriangle className="w-5 h-5" />
          <span>Error loading usage</span>
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
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col">
          <h1 className="font-playfair text-3xl font-bold text-primary">External API usage</h1>
          <p className="text-on-surface-variant font-literata text-sm mt-1">
            Quota units consumed against YouTube, TikTok and third-party providers.
          </p>
        </div>
        <div className="flex items-center gap-1">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setDays(r)}
              className={cn(
                "px-4 py-2 rounded-full text-xs font-literata font-semibold transition-colors",
                days === r
                  ? "bg-primary text-on-primary"
                  : "border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container",
              )}
            >
              {r}d
            </button>
          ))}
        </div>
      </div>

      {loading || !usage ? (
        <div className="flex flex-col gap-6 animate-pulse">
          <div className="grid sm:grid-cols-2 gap-6">
            <div className="h-28 bg-surface-container rounded-2xl" />
            <div className="h-28 bg-surface-container rounded-2xl" />
          </div>
          <div className="h-56 bg-surface-container rounded-3xl" />
          <div className="h-56 bg-surface-container rounded-3xl" />
        </div>
      ) : (
        <>
          <div className="grid sm:grid-cols-2 gap-6">
            <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl p-6 shadow-sm">
              <span className="text-[10px] text-on-surface-variant font-medium uppercase tracking-wider">
                Units today
              </span>
              <div className="font-playfair text-3xl font-extrabold text-primary mt-2">
                {formatNumber(usage.units_today)}
              </div>
            </div>
            <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl p-6 shadow-sm">
              <span className="text-[10px] text-on-surface-variant font-medium uppercase tracking-wider">
                Units in last {usage.days}d
              </span>
              <div className="font-playfair text-3xl font-extrabold text-primary mt-2">
                {formatNumber(usage.units_window)}
              </div>
            </div>
          </div>

          <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm">
            <h3 className="font-playfair text-lg font-bold text-primary mb-6">
              Daily units — last {usage.days} days
            </h3>
            <BarChart
              data={usage.series.map((p) => ({ label: p.date, value: p.units }))}
              height={160}
            />
            <div className="flex justify-between text-[10px] text-on-surface-variant font-literata mt-2">
              <span>{usage.series[0]?.date}</span>
              <span>{usage.series[usage.series.length - 1]?.date}</span>
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm">
              <h3 className="font-playfair text-lg font-bold text-primary mb-4">
                By endpoint
              </h3>
              {usage.by_endpoint.length === 0 ? (
                <p className="font-literata text-sm text-on-surface-variant/60 italic">
                  No API calls recorded in this window.
                </p>
              ) : (
                <div className="flex flex-col gap-3">
                  {usage.by_endpoint.map((e) => (
                    <div
                      key={e.endpoint}
                      className="flex items-center justify-between text-sm font-literata"
                    >
                      <span className="text-on-surface-variant">{e.endpoint}</span>
                      <span className="text-primary font-semibold">
                        {formatNumber(e.units)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm">
              <h3 className="font-playfair text-lg font-bold text-primary mb-4">
                Top consumers
              </h3>
              {usage.top_consumers.length === 0 ? (
                <p className="font-literata text-sm text-on-surface-variant/60 italic">
                  No usage recorded in this window.
                </p>
              ) : (
                <div className="flex flex-col gap-3">
                  {usage.top_consumers.map((c) => (
                    <div
                      key={c.user_id}
                      className="flex items-center justify-between text-sm font-literata gap-4"
                    >
                      <span className="text-on-surface-variant truncate">{c.email}</span>
                      <span className="text-primary font-semibold flex-shrink-0">
                        {formatNumber(c.units)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </motion.div>
  );
}
