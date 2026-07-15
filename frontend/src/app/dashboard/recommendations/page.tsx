"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Lightbulb, Check, Rocket, X, ArrowRight, Sparkles } from "lucide-react";

// ─── Types (must mirror what we store in video detail page) ──────────────────
type RecStatus = "none" | "planned" | "in_progress" | "dismissed";

interface RecMeta {
  status: RecStatus;
  title: string;
  content: string;
  videoId: string;
  videoTitle: string;
}

const LS_KEY = "olundi_recs";

// ─── Status config ────────────────────────────────────────────────────────────
const STATUS_CONFIG: Record<RecStatus, { label: string; color: string; dot: string }> = {
  none:        { label: "Unreviewed",  color: "bg-neutral-100 text-neutral-500 border-neutral-200", dot: "bg-neutral-400" },
  planned:     { label: "Planned",     color: "bg-amber-100 text-amber-800 border-amber-200",        dot: "bg-amber-400"  },
  in_progress: { label: "In Progress", color: "bg-sky-100 text-sky-800 border-sky-200",              dot: "bg-sky-400"    },
  dismissed:   { label: "Dismissed",   color: "bg-rose-50 text-rose-500 border-rose-200",            dot: "bg-rose-400"   },
};

const KANBAN_ORDER: RecStatus[] = ["planned", "in_progress", "none", "dismissed"];

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<Record<string, RecMeta>>({});
  const [activeFilter, setActiveFilter] = useState<RecStatus | "all">("all");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem(LS_KEY) || "{}") as Record<string, RecMeta>;
      setRecs(stored);
    } catch {
      setRecs({});
    }
    setLoaded(true);
  }, []);

  const allEntries = Object.entries(recs); // [id, RecMeta][]
  const hasAny = allEntries.length > 0;

  // Kanban counts
  const counts: Record<RecStatus | "all", number> = {
    all:         allEntries.length,
    none:        allEntries.filter(([, m]) => m.status === "none").length,
    planned:     allEntries.filter(([, m]) => m.status === "planned").length,
    in_progress: allEntries.filter(([, m]) => m.status === "in_progress").length,
    dismissed:   allEntries.filter(([, m]) => m.status === "dismissed").length,
  };

  // Filtered list
  const filtered = activeFilter === "all"
    ? allEntries
    : allEntries.filter(([, m]) => m.status === activeFilter);

  // Update status in state + localStorage
  const setStatus = (id: string, status: RecStatus) => {
    setRecs(prev => {
      const updated = { ...prev, [id]: { ...prev[id], status } };
      try { localStorage.setItem(LS_KEY, JSON.stringify(updated)); } catch { /* noop */ }
      return updated;
    });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="flex flex-col gap-8"
    >
      {/* Page header */}
      <div className="flex flex-col gap-1">
        <h1 className="font-playfair text-2xl font-bold text-primary">Content Opportunities</h1>
        <p className="text-sm font-literata text-on-surface-variant">
          Track all AI-suggested content ideas across your analysed videos.
        </p>
      </div>

      {!loaded ? (
        <div className="animate-pulse flex flex-col gap-4">
          <div className="h-20 bg-surface-container rounded-3xl" />
          <div className="grid md:grid-cols-3 gap-4">
            {[1,2,3].map(i => <div key={i} className="h-40 bg-surface-container rounded-2xl" />)}
          </div>
        </div>
      ) : !hasAny ? (
        /* Empty state */
        <div className="flex flex-col items-center gap-5 py-24 text-center max-w-md mx-auto">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <Lightbulb className="w-7 h-7 text-primary" />
          </div>
          <h2 className="font-playfair text-xl font-bold text-primary">No opportunities yet</h2>
          <p className="font-literata text-sm text-on-surface-variant leading-relaxed">
            Analyse a video to let the AI surface content ideas based on what your audience is asking for.
          </p>
          <Link
            href="/dashboard/videos"
            className="flex items-center gap-2 px-6 py-3 rounded-full bg-primary text-on-primary font-literata font-semibold text-sm shadow-md hover:opacity-90 transition"
          >
            <Sparkles className="w-4 h-4" />
            Go to My Videos
          </Link>
        </div>
      ) : (
        <>
          {/* Kanban summary row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {KANBAN_ORDER.map(status => {
              const cfg = STATUS_CONFIG[status];
              const count = counts[status];
              const icons: Record<RecStatus, React.ReactNode> = {
                none:        <Lightbulb className="w-4 h-4" />,
                planned:     <Check className="w-4 h-4" />,
                in_progress: <Rocket className="w-4 h-4" />,
                dismissed:   <X className="w-4 h-4" />,
              };
              return (
                <button
                  key={status}
                  onClick={() => setActiveFilter(activeFilter === status ? "all" : status)}
                  className={`flex items-center gap-3 p-5 rounded-2xl border text-left transition cursor-pointer ${ 
                    activeFilter === status
                      ? cfg.color + " shadow-sm"
                      : "bg-white border-outline-variant/10 hover:shadow-sm hover:bg-surface-container"
                  }`}
                >
                  <span className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${ activeFilter === status ? "bg-white/40" : "bg-surface-container" }`}>
                    {icons[status]}
                  </span>
                  <div className="flex flex-col">
                    <span className="text-xl font-bold font-playfair leading-none">{count}</span>
                    <span className="text-[11px] font-literata font-medium opacity-70">{cfg.label}</span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* All / filter toggle */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveFilter("all")}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold font-literata border transition cursor-pointer ${
                activeFilter === "all"
                  ? "bg-primary text-on-primary border-primary"
                  : "border-outline-variant/20 text-on-surface-variant hover:bg-surface-container"
              }`}
            >
              All ({counts.all})
            </button>
            <span className="text-xs text-on-surface-variant/40 font-literata">— or click a card above to filter</span>
          </div>

          {/* Recommendation list */}
          {filtered.length === 0 ? (
            <div className="text-center py-12 font-literata text-sm text-on-surface-variant/60 italic">
              No recommendations with this status.
            </div>
          ) : (
            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">
              {filtered.map(([id, meta]) => {
                const cfg = STATUS_CONFIG[meta.status];
                const isDismissed = meta.status === "dismissed";
                return (
                  <div
                    key={id}
                    className={`relative bg-white border border-outline-variant/10 rounded-2xl p-5 shadow-sm flex flex-col justify-between transition ${ isDismissed ? "opacity-50" : "hover:shadow" }`}
                  >
                    {/* Status chip */}
                    <span className={`absolute top-3 right-3 text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full border ${cfg.color}`}>
                      {cfg.label}
                    </span>

                    <div className="flex flex-col gap-2">
                      {/* Video source */}
                      <Link
                        href={`/dashboard/videos/${meta.videoId}`}
                        className="flex items-center gap-1 text-[10px] font-literata text-on-surface-variant/60 hover:text-primary transition w-fit"
                      >
                        <ArrowRight className="w-2.5 h-2.5" />
                        <span className="truncate max-w-[160px]">{meta.videoTitle}</span>
                      </Link>

                      <h3 className={`font-playfair text-sm font-bold pr-16 leading-snug ${ isDismissed ? "line-through text-on-surface-variant" : "text-primary" }`}>
                        {meta.title}
                      </h3>
                      <p className="text-xs font-literata text-on-surface-variant leading-relaxed">
                        {meta.content}
                      </p>
                    </div>

                    {/* Action row */}
                    <div className="flex items-center gap-2 mt-4 pt-3 border-t border-outline-variant/10">
                      {isDismissed ? (
                        <button
                          onClick={() => setStatus(id, "none")}
                          className="text-xs font-semibold font-literata text-primary hover:underline cursor-pointer"
                        >
                          Restore
                        </button>
                      ) : (
                        <>
                          <button
                            onClick={() => setStatus(id, meta.status === "planned" ? "none" : "planned")}
                            className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold font-literata border transition cursor-pointer ${ meta.status === "planned" ? "bg-amber-100 text-amber-800 border-amber-300" : "bg-surface-container text-on-surface-variant border-outline-variant/20 hover:bg-amber-50 hover:text-amber-800" }`}
                          >
                            <Check className="w-3 h-3" /> Planned
                          </button>
                          <button
                            onClick={() => setStatus(id, meta.status === "in_progress" ? "none" : "in_progress")}
                            className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold font-literata border transition cursor-pointer ${ meta.status === "in_progress" ? "bg-sky-100 text-sky-800 border-sky-300" : "bg-surface-container text-on-surface-variant border-outline-variant/20 hover:bg-sky-50 hover:text-sky-800" }`}
                          >
                            <Rocket className="w-3 h-3" /> In Progress
                          </button>
                          <button
                            onClick={() => setStatus(id, "dismissed")}
                            className="ml-auto p-1.5 rounded-full text-on-surface-variant/40 hover:text-rose-500 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition cursor-pointer"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}
