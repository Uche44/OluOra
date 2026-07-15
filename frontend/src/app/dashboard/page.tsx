"use client";

import React, { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { authedFetch } from "@/lib/api";
import {
  TrendingUp,
  MessageSquare,
  AlertTriangle,
  X,
  Play,
  HelpCircle,
  Sparkle,
  Loader2,
  Video,
  ArrowRight,
  TrendingDown,
  BarChart2,
} from "lucide-react";

interface DashboardStats {
  videos_analyzed: number;
  comments_processed: number;
  questions_discovered: number;
  sentiment_score: number;
  growth_score: number;
  summary_title: string;
  summary_content: string;
  summary_date: string;
  summary_metrics: { label: string; value: string }[];
  recent_actions: {
    id: string;
    type: string;
    title: string;
    description: string;
    buttonText: string;
  }[];
}

export default function DashboardPage() {
  const [statsData, setStatsData] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatorName, setCreatorName] = useState("Creator");

  // Load creator name from local storage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("user");
      if (stored) {
        const u = JSON.parse(stored);
        if (u.full_name) {
          setCreatorName(u.full_name.split(" ")[0]); // just first name
        }
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  const fetchDashboardStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await authedFetch(`${apiUrl}/api/v1/users/dashboard`);
      if (!res.ok) {
        throw new Error("Failed to load dashboard data.");
      }
      const data = await res.json();
      setStatsData(data);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An error occurred fetching dashboard metrics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardStats();
  }, [fetchDashboardStats]);

  // Action dismisser handler
  const handleDismissAction = (actionId: string) => {
    if (!statsData) return;
    setStatsData({
      ...statsData,
      recent_actions: statsData.recent_actions.filter((a) => a.id !== actionId),
    });
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "K";
    return num.toString();
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-8 animate-pulse text-on-surface p-2">
        <div className="flex flex-col gap-2">
          <div className="h-8 bg-surface-container rounded-lg w-1/3" />
          <div className="h-4 bg-surface-container rounded-lg w-1/2" />
        </div>
        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 h-72 bg-surface-container rounded-3xl" />
          <div className="h-72 bg-surface-container rounded-3xl" />
        </div>
        <div className="h-44 bg-surface-container rounded-3xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 text-red-900 rounded-3xl flex flex-col gap-4 font-literata text-sm max-w-xl mx-auto my-12">
        <div className="flex items-center gap-2 text-red-700 font-bold">
          <AlertTriangle className="w-5 h-5" />
          <span>Error Loading Dashboard</span>
        </div>
        <p>{error}</p>
        <button
          onClick={fetchDashboardStats}
          className="px-5 py-2 rounded-full bg-red-700 text-white font-semibold self-start hover:bg-red-800 transition"
        >
          Retry
        </button>
      </div>
    );
  }

  const stats = [
    {
      label: "Videos Analyzed",
      value: statsData ? formatNumber(statsData.videos_analyzed) : "0",
      icon: Play,
    },
    {
      label: "Comments Processed",
      value: statsData ? formatNumber(statsData.comments_processed) : "0",
      icon: MessageSquare,
    },
    {
      label: "Questions Discovered",
      value: statsData ? formatNumber(statsData.questions_discovered) : "0",
      icon: HelpCircle,
    },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-8 text-on-surface"
    >
      {/* Welcome Bar Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col">
          <h1 className="font-playfair text-3xl font-bold text-primary">
            Good morning, {creatorName}
          </h1>
          <p className="text-on-surface-variant font-literata text-sm mt-1 max-w-xl leading-relaxed">
            {statsData?.videos_analyzed && statsData.videos_analyzed > 0
              ? "Here is your audience's compilation overview and latest audience insights."
              : "Welcome to OluOra. Connect your channel and start analyzing comment themes to generate recommendations."}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard/videos"
            className="px-5 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition-all duration-150 flex items-center gap-1.5 shadow-sm cursor-pointer"
          >
            <span>Go to Video Library</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Main Grid: Today's Summary & Audience Health */}
      <div className="grid lg:grid-cols-3 gap-8 items-start">
        {/* Large Summary Card */}
        <div className="lg:col-span-2 bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col justify-between min-h-[340px] relative overflow-hidden group hover:shadow-md transition-shadow">
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="inline-flex items-center gap-2">
                <span className="ai-badge">AI Insights</span>
                <span className="text-[10px] text-on-surface-variant/80 font-literata">
                  {statsData?.summary_date}
                </span>
              </div>
            </div>

            <h2 className="font-playfair text-2xl font-bold text-primary">
              {statsData?.summary_title}
            </h2>
            <p className="text-on-surface-variant font-literata text-sm leading-relaxed mt-1">
              {statsData?.summary_content}
            </p>
          </div>

          <div className="flex items-center gap-6 mt-8 border-t border-outline-variant/20 pt-6">
            {statsData?.summary_metrics.map((metric, idx) => (
              <div
                key={idx}
                className="flex items-center gap-2 text-xs font-literata font-medium text-emerald-700"
              >
                <TrendingUp className="w-4 h-4" />
                <span>
                  {metric.value} {metric.label}
                </span>
              </div>
            ))}
            {(!statsData?.summary_metrics ||
              statsData.summary_metrics.length === 0) && (
              <span className="text-xs font-literata text-on-surface-variant/50 italic">
                No active metrics yet
              </span>
            )}
          </div>

          {/* Magic Wand Visual Overlay */}
          <div className="absolute right-6 top-8 w-24 h-24 opacity-10 pointer-events-none group-hover:opacity-15 transition-opacity">
            <svg
              viewBox="0 0 100 100"
              className="w-full h-full fill-primary"
            >
              <path d="M78.6 30.6c1-1 1-2.6 0-3.6L73 21.4c-1-1-2.6-1-3.6 0L24.8 66c-1 1-1 2.6 0 3.6l5.6 5.6c1 1 2.6 1 3.6 0l44.6-44.6zM88 40v4c0 1.1-.9 2-2 2s-2-.9-2-2v-4c0-1.1.9-2 2-2s2 .9 2 2zm-58 48v4c0 1.1-.9 2-2 2s-2-.9-2-2v-4c0-1.1.9-2 2-2s2 .9 2 2zm34-6c0-1.1.9-2 2-2h4c1.1 0 2 .9 2 2s-.9 2-2 2h-4c-1.1 0-2-.9-2-2z" />
            </svg>
          </div>
        </div>

        {/* Audience Health Card */}
        <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col items-center justify-between min-h-[340px] hover:shadow-md transition-shadow">
          <div className="w-full flex items-center justify-between">
            <h3 className="font-playfair text-lg font-bold text-primary">
              Audience Sentiment
            </h3>
            <span className="text-[10px] text-on-surface-variant/80 font-literata">
              Composite
            </span>
          </div>

          {/* SVG Progress Circle */}
          <div className="relative w-36 h-36 flex items-center justify-center my-4">
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="72"
                cy="72"
                r="56"
                className="stroke-surface-container"
                strokeWidth="8"
                fill="none"
              />
              <circle
                cx="72"
                cy="72"
                r="56"
                className="stroke-[#0b3d2e]"
                strokeWidth="8"
                fill="none"
                strokeDasharray={351.8}
                strokeDashoffset={
                  351.8 * (1 - (statsData?.sentiment_score ?? 75) / 100)
                }
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute flex flex-col items-center">
              <span className="font-playfair text-3xl font-extrabold text-primary">
                {statsData?.sentiment_score ?? 75}%
              </span>
              <span className="text-[9px] text-on-surface-variant font-medium tracking-widest uppercase mt-0.5">
                Sentiment Score
              </span>
            </div>
          </div>

          <div className="w-full grid grid-cols-2 gap-3 mt-2">
            <div className="bg-surface-container-low border border-outline-variant/10 rounded-2xl p-3 text-center">
              <span className="text-[9px] text-on-surface-variant/80 font-medium tracking-wider uppercase block">
                Resonance
              </span>
              <span className="font-playfair text-sm font-bold text-primary mt-0.5 block">
                {(statsData?.sentiment_score ?? 75) > 80
                  ? "Stunning"
                  : "Harmonic"}
              </span>
            </div>
            <div className="bg-surface-container-low border border-outline-variant/10 rounded-2xl p-3 text-center">
              <span className="text-[9px] text-on-surface-variant/80 font-medium tracking-wider uppercase block">
                Prevalence
              </span>
              <span className="font-playfair text-sm font-bold text-primary mt-0.5 block">
                {statsData?.growth_score ?? 88}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Row of Statistics Cards */}
      <div className="grid sm:grid-cols-3 gap-6">
        {stats.map((stat, idx) => {
          const Icon = stat.icon;
          return (
            <div
              key={idx}
              className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl p-6 shadow-sm flex items-center gap-4 hover:shadow-md transition-shadow"
            >
              <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center border border-outline-variant/20 flex-shrink-0">
                <Icon className="w-5 h-5 text-primary" />
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-on-surface-variant font-medium uppercase tracking-wider">
                  {stat.label}
                </span>
                <span className="font-playfair text-2xl font-extrabold text-primary leading-tight mt-0.5">
                  {stat.value}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Recommended Actions */}
      <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col gap-6 hover:shadow-md transition-shadow">
        <div className="flex items-center justify-between border-b border-outline-variant/20 pb-4">
          <h3 className="font-playfair text-lg font-bold text-primary">
            Recommended Actions
          </h3>
          <Link
            href="/dashboard/recommendations"
            className="text-xs font-semibold font-literata text-[#735c00] hover:underline"
          >
            View All Opportunities
          </Link>
        </div>

        <div className="flex flex-col gap-5">
          {statsData?.recent_actions && statsData.recent_actions.length > 0 ? (
            statsData.recent_actions.map((action) => {
              const Icon =
                action.type === "alert"
                  ? AlertTriangle
                  : action.type === "trend"
                    ? TrendingUp
                    : Sparkle;
              const iconBg =
                action.type === "alert"
                  ? "bg-amber-100 text-amber-700"
                  : action.type === "trend"
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-indigo-100 text-indigo-700";

              return (
                <div
                  key={action.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 hover:bg-surface-container/30 rounded-2xl transition-colors duration-150 group border border-transparent hover:border-outline-variant/10"
                >
                  <div className="flex gap-4 items-start">
                    <div
                      className={`p-3 rounded-xl ${iconBg} flex-shrink-0 mt-0.5`}
                    >
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex flex-col gap-1">
                      <h4 className="font-playfair text-base font-bold text-primary">
                        {action.title}
                      </h4>
                      <p className="text-xs text-on-surface-variant font-literata leading-relaxed max-w-xl">
                        {action.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-center">
                    <button className="px-4 py-2 border border-outline-variant/30 text-xs font-semibold font-literata rounded-xl text-primary hover:bg-surface-container transition-all cursor-pointer whitespace-nowrap">
                      {action.buttonText}
                    </button>
                    <button
                      onClick={() => handleDismissAction(action.id)}
                      aria-label="Dismiss recommendation"
                      className="p-2 rounded-lg text-on-surface-variant/40 hover:text-error hover:bg-error-container/10 transition-all cursor-pointer"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="text-center py-10 font-literata text-xs text-on-surface-variant/60 italic">
              No recommended actions found. Sync and analyze a video from your
              library to discover opportunities.
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
