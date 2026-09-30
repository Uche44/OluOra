"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  Users,
  MessageSquare,
  Video,
  Sparkles,
  ClipboardList,
  Activity,
  AlertTriangle,
} from "lucide-react";
import { formatNumber } from "@/lib/utils";
import { getJson } from "@/lib/http";
import { BarChart } from "@/components/charts/BarChart";

interface Overview {
  total_users: number;
  active_users: number;
  inactive_users: number;
  new_users_7d: number;
  new_users_30d: number;
  plan_split: Record<string, number>;
  waitlist_total: number;
  waitlist_7d: number;
  waitlist_30d: number;
  total_channels: number;
  channels_by_platform: Record<string, number>;
  total_videos: number;
  total_comments: number;
  total_analyses: number;
  total_insights: number;
  connected_accounts: Record<string, number>;
}

interface GrowthPoint {
  date: string;
  users: number;
  waitlist: number;
  comments: number;
  analyses: number;
  insights: number;
}

interface Growth {
  days: number;
  points: GrowthPoint[];
}

const card =
  "bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow";

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className={card}>
      <div className="flex items-start justify-between">
        <span className="text-[10px] text-on-surface-variant font-medium uppercase tracking-wider">
          {label}
        </span>
        <div className="w-9 h-9 rounded-xl bg-surface-container flex items-center justify-center border border-outline-variant/20 flex-shrink-0">
          <Icon className="w-4 h-4 text-primary" />
        </div>
      </div>
      <div className="font-playfair text-3xl font-extrabold text-primary mt-2">
        {value}
      </div>
      {sub && (
        <div className="text-[11px] text-on-surface-variant font-literata mt-1">
          {sub}
        </div>
      )}
    </div>
  );
}

export default function OverviewPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [growth, setGrowth] = useState<Growth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, gr] = await Promise.all([
        getJson<Overview>("/admin/overview"),
        getJson<Growth>("/admin/growth?days=30"),
      ]);
      setOverview(ov);
      setGrowth(gr);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex flex-col gap-8 animate-pulse p-2">
        <div className="h-8 bg-surface-container rounded-lg w-1/3" />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {Array.from({ length: 8 }).map((_, i) => (
            <div
              key={i}
              className="h-28 bg-surface-container rounded-2xl"
            />
          ))}
        </div>
        <div className="h-64 bg-surface-container rounded-3xl" />
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 text-red-900 rounded-3xl flex flex-col gap-4 font-literata text-sm max-w-xl">
        <div className="flex items-center gap-2 text-red-700 font-bold">
          <AlertTriangle className="w-5 h-5" />
          <span>Error loading metrics</span>
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

  const points = growth?.points ?? [];
  const youtube = overview.connected_accounts?.youtube ?? 0;
  const tiktok = overview.connected_accounts?.tiktok ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-8 text-on-surface"
    >
      <div className="flex flex-col">
        <h1 className="font-playfair text-3xl font-bold text-primary">
          Platform overview
        </h1>
        <p className="text-on-surface-variant font-literata text-sm mt-1">
          Top-line growth and usage across OluOra. Data is live.
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          label="Total users"
          value={formatNumber(overview.total_users)}
          sub={`${overview.active_users} active · ${overview.inactive_users} suspended`}
          icon={Users}
        />
        <StatCard
          label="New users (7d)"
          value={formatNumber(overview.new_users_7d)}
          sub={`${formatNumber(overview.new_users_30d)} in last 30d`}
          icon={TrendingUp}
        />
        <StatCard
          label="Waitlist"
          value={formatNumber(overview.waitlist_total)}
          sub={`+${overview.waitlist_7d} this week`}
          icon={ClipboardList}
        />
        <StatCard
          label="Plan split"
          value={`${overview.plan_split?.free ?? 0} / ${overview.plan_split?.pro ?? 0}`}
          sub="free / pro"
          icon={Activity}
        />
        {/* <StatCard
          label="Comments processed"
          value={formatNumber(overview.total_comments)}
          sub="across all videos"
          icon={MessageSquare}
        /> */}
        <StatCard
          label="Videos synced"
          value={formatNumber(overview.total_videos)}
          sub={`${formatNumber(overview.total_channels)} channels`}
          icon={Video}
        />
        <StatCard
          label="Insights generated"
          value={formatNumber(overview.total_insights)}
          sub={`${formatNumber(overview.total_analyses)} analyses run`}
          icon={Sparkles}
        />
        <StatCard
          label="Connected accounts"
          value={formatNumber(youtube + tiktok)}
          sub={`${youtube} YouTube · ${tiktok} TikTok`}
          icon={Activity}
        />
      </div>

      <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-playfair text-lg font-bold text-primary">
            Signups — last 30 days
          </h3>
          <span className="text-[10px] text-on-surface-variant font-literata">
            users ({formatNumber(points.reduce((a, p) => a + p.users, 0))})
          </span>
        </div>
        <BarChart
          data={points.map((p) => ({ label: p.date, value: p.users }))}
          height={180}
        />
        <div className="flex justify-between text-[10px] text-on-surface-variant font-literata mt-2">
          <span>{points[0]?.date}</span>
          <span>{points[points.length - 1]?.date}</span>
        </div>
      </div>

      <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <h3 className="font-playfair text-lg font-bold text-primary">
            Waitlist signups — last 30 days
          </h3>
          <span className="text-[10px] text-on-surface-variant font-literata">
            {formatNumber(points.reduce((a, p) => a + p.waitlist, 0))} total
          </span>
        </div>
        <BarChart
          data={points.map((p) => ({ label: p.date, value: p.waitlist }))}
          height={140}
          color="var(--secondary)"
        />
      </div>
    </motion.div>
  );
}
