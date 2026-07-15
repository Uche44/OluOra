"use client";

import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { authedFetch } from "@/lib/api";
import {
  Lightbulb,
  Search,
  MessageSquare,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  Play,
  Clock,
  Sparkles
} from "lucide-react";

interface VideoReport {
  id: string;
  youtube_video_id: string;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  published_at: string | null;
  view_count: number;
  like_count: number;
  comment_count: number;
  sync_status: string;
}

export default function InsightsHubPage() {
  const [reports, setReports] = useState<VideoReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      // Fetch only videos that have been analyzed (status=analyzed)
      const res = await authedFetch(`${apiUrl}/api/v1/videos?status=analyzed&limit=100`);
      if (!res.ok) {
        throw new Error("Failed to load audience reports.");
      }
      const json = await res.json();
      setReports(json.data || []);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred loading insights reports.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Filtered reports list
  const filtered = reports.filter(r => 
    r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (r.description && r.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "";
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "K";
    return num.toString();
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-6 animate-pulse text-on-surface p-2">
        <div className="h-8 bg-surface-container rounded-lg w-1/4" />
        <div className="h-10 bg-surface-container rounded-lg w-full max-w-md" />
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mt-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-64 bg-surface-container rounded-3xl" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 text-red-900 rounded-3xl flex flex-col gap-4 font-literata text-sm max-w-xl mx-auto my-12">
        <div className="flex items-center gap-2 text-red-700 font-bold">
          <AlertTriangle className="w-5 h-5" />
          <span>Error Loading Insights</span>
        </div>
        <p>{error}</p>
        <button onClick={fetchReports} className="px-5 py-2 rounded-full bg-red-700 text-white font-semibold self-start hover:bg-red-800 transition">
          Retry
        </button>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="flex flex-col gap-8 text-on-surface"
    >
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="font-playfair text-3xl font-bold text-primary">Audience Intelligence Hub</h1>
        <p className="text-sm font-literata text-on-surface-variant">
          Access complete audience segments, sentiment indexes, and interest themes for your analyzed uploads.
        </p>
      </div>

      {reports.length === 0 ? (
        /* Empty State */
        <div className="flex flex-col items-center gap-5 py-24 text-center max-w-md mx-auto">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <Lightbulb className="w-7 h-7 text-primary" />
          </div>
          <h2 className="font-playfair text-xl font-bold text-primary">No Reports Compiled Yet</h2>
          <p className="font-literata text-sm text-on-surface-variant leading-relaxed">
            Audience reports are generated when you run comment analysis on a video. Sync and analyze a video to start collecting insights.
          </p>
          <Link
            href="/dashboard/videos"
            className="flex items-center gap-2 px-6 py-3 rounded-full bg-primary text-on-primary font-literata font-semibold text-sm shadow-md hover:opacity-90 transition cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            Go to Video Library
          </Link>
        </div>
      ) : (
        <>
          {/* Search bar */}
          <div className="relative max-w-md w-full">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/50" />
            <input
              type="text"
              placeholder="Search reports by title..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-full border border-outline-variant/30 text-sm font-literata focus:ring-1 focus:ring-primary focus:outline-none bg-white/70 backdrop-blur-sm"
            />
          </div>

          {/* Grid of video reports */}
          {filtered.length === 0 ? (
            <div className="text-center py-12 font-literata text-sm text-on-surface-variant/60 italic">
              No reports match your search query.
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filtered.map((report) => (
                <div
                  key={report.id}
                  className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl overflow-hidden shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between"
                >
                  <div className="flex flex-col">
                    {/* Video Thumbnail */}
                    <div className="relative aspect-video w-full bg-surface-container overflow-hidden border-b border-outline-variant/10">
                      {report.thumbnail_url ? (
                        <img
                          src={report.thumbnail_url}
                          alt={report.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Play className="w-10 h-10 text-on-surface-variant/20" />
                        </div>
                      )}
                      <span className="absolute bottom-3 right-3 text-[9px] font-bold tracking-wider px-2 py-0.5 rounded bg-black/60 text-white flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDate(report.published_at)}
                      </span>
                    </div>

                    <div className="p-6 flex flex-col gap-3">
                      <h3 className="font-playfair text-base font-bold text-primary line-clamp-2 leading-snug">
                        {report.title}
                      </h3>
                      
                      <div className="flex items-center gap-4 mt-2 text-xs font-literata text-on-surface-variant font-medium">
                        <div className="flex items-center gap-1">
                          <MessageSquare className="w-3.5 h-3.5 text-primary" />
                          <span>{formatNumber(report.comment_count)} Comments</span>
                        </div>
                        <div className="flex items-center gap-1 border-l border-outline-variant/30 pl-4">
                          <TrendingUp className="w-3.5 h-3.5 text-emerald-700" />
                          <span>Report Ready</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="px-6 pb-6 pt-2 border-t border-outline-variant/10 flex">
                    <Link
                      href={`/dashboard/videos/${report.id}`}
                      className="w-full py-2.5 rounded-full bg-surface-container hover:bg-primary hover:text-on-primary text-primary font-literata text-xs font-semibold text-center flex items-center justify-center gap-1.5 transition-all cursor-pointer"
                    >
                      <span>Explore Report</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}
