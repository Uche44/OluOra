"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Calendar,
  Check,
  Film,
  Lightbulb,
  Loader2,
  MessageSquare,
  Quote,
  RefreshCw,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { authedFetch } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  VideoSourceSelect,
  type AnalysisSource,
} from "@/components/dashboard/VideoSourceSelect";

type OpportunityStatus = "new" | "saved" | "dismissed";

interface Evidence {
  id: string;
  insight_id: string | null;
  cluster_id: string | null;
  comment_id: string | null;
  quote: string | null;
}

interface Opportunity {
  id: string;
  analysis_id: string | null;
  source_video_id: string | null;
  source_video_title: string | null;
  title: string;
  rationale: string;
  suggested_format: string;
  suggested_length: string;
  suggested_angle: string;
  priority: string;
  status: OpportunityStatus;
  is_evidence_backed: boolean;
  is_scheduled: boolean;
  scheduled_dates: string[];
  generated_at: string;
  evidence: Evidence[];
}

const PRIORITY_STYLES: Record<string, string> = {
  high: "bg-rose-50 text-rose-700 border-rose-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-slate-50 text-slate-600 border-slate-200",
};

const STATUS_STYLES: Record<OpportunityStatus, string> = {
  new: "bg-sky-50 text-sky-700 border-sky-200",
  saved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  dismissed: "bg-neutral-100 text-neutral-500 border-neutral-200",
};

const LENGTH_LABELS: Record<string, string> = {
  long_form: "Long-form",
  short: "Short",
};

function formatScheduledDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function todayIso() {
  const value = new Date();
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function evidenceLabel(evidence: Evidence) {
  if (evidence.comment_id) return "Viewer comment";
  if (evidence.insight_id) return "Analysis insight";
  if (evidence.cluster_id) return "Topic theme";
  return "Audience evidence";
}

export default function OpportunitiesPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [sources, setSources] = useState<AnalysisSource[]>([]);
  const [selectedAnalysisId, setSelectedAnalysisId] = useState("");
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [statusFilter, setStatusFilter] = useState<"all" | OpportunityStatus>("all");
  const [loadingSources, setLoadingSources] = useState(true);
  const [loadingOpportunities, setLoadingOpportunities] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Add-to-calendar dialog
  const [calendarOpportunity, setCalendarOpportunity] = useState<Opportunity | null>(null);
  const [calendarDate, setCalendarDate] = useState(todayIso);
  const [calendarTime, setCalendarTime] = useState("");
  const [addingToCalendar, setAddingToCalendar] = useState(false);

  const fetchSources = useCallback(async () => {
    setLoadingSources(true);
    try {
      const res = await authedFetch(`${apiUrl}/api/v1/content/opportunities/sources`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail?.message || "Could not load analyzed videos.");
      }
      const nextSources: AnalysisSource[] = data.data || [];
      setSources(nextSources);
      // Sources are one-per-video (latest run). Drop a selection that is no
      // longer offered, e.g. after a re-analysis replaced the run we held.
      setSelectedAnalysisId((current) =>
        nextSources.some((source) => source.analysis_id === current)
          ? current
          : nextSources[0]?.analysis_id || "",
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load analyzed videos.",
      );
    } finally {
      setLoadingSources(false);
    }
  }, [apiUrl]);

  const fetchOpportunities = useCallback(async () => {
    setLoadingOpportunities(true);
    try {
      const res = await authedFetch(`${apiUrl}/api/v1/content/opportunities?limit=100`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail?.message || "Could not load opportunities.");
      }
      setOpportunities(data.data || []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not load opportunities.",
      );
    } finally {
      setLoadingOpportunities(false);
    }
  }, [apiUrl]);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    fetchSources();
    fetchOpportunities();
  }, [fetchSources, fetchOpportunities]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const selectedSource = sources.find((s) => s.analysis_id === selectedAnalysisId);

  const counts = useMemo(
    () => ({
      all: opportunities.length,
      new: opportunities.filter((o) => o.status === "new").length,
      saved: opportunities.filter((o) => o.status === "saved").length,
      dismissed: opportunities.filter((o) => o.status === "dismissed").length,
    }),
    [opportunities],
  );

  const visibleOpportunities = useMemo(
    () =>
      statusFilter === "all"
        ? opportunities
        : opportunities.filter((o) => o.status === statusFilter),
    [opportunities, statusFilter],
  );

  const handleGenerate = async (force = false) => {
    if (!selectedAnalysisId) return;
    setGenerating(true);
    setError(null);
    setNotice(null);
    try {
      const res = await authedFetch(`${apiUrl}/api/v1/content/opportunities/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_id: selectedAnalysisId,
          limit: 3,
          force,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          data?.detail?.message || "Could not generate opportunities.",
        );
      }
      setNotice(
        data.cached
          ? "Showing opportunities previously generated for this analysis. Use Regenerate to create a fresh set."
          : "Generated new evidence-backed opportunities.",
      );
      await fetchOpportunities();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not generate opportunities.",
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleStatus = async (opportunity: Opportunity, status: OpportunityStatus) => {
    const previous = opportunities;
    setOpportunities((items) =>
      items.map((item) => (item.id === opportunity.id ? { ...item, status } : item)),
    );
    try {
      const res = await authedFetch(
        `${apiUrl}/api/v1/content/opportunities/${opportunity.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status }),
        },
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail?.message || "Could not update the opportunity.");
      }
    } catch (err) {
      setOpportunities(previous);
      setError(
        err instanceof Error ? err.message : "Could not update the opportunity.",
      );
    }
  };

  const openCalendarDialog = (opportunity: Opportunity) => {
    setCalendarOpportunity(opportunity);
    setCalendarDate(todayIso());
    setCalendarTime("");
    setError(null);
    setNotice(null);
  };

  const handleAddToCalendar = async () => {
    if (!calendarOpportunity) return;
    setAddingToCalendar(true);
    setError(null);
    try {
      const res = await authedFetch(`${apiUrl}/api/v1/content/calendar/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          opportunity_id: calendarOpportunity.id,
          scheduled_date: calendarDate,
          scheduled_time: calendarTime || null,
          status: "planned",
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail?.message || "Could not add this to the calendar.");
      }
      const addedOpportunity = calendarOpportunity;
      const addedDate = calendarDate;
      setOpportunities((items) =>
        items.map((item) =>
          item.id === addedOpportunity.id
            ? {
                ...item,
                is_scheduled: true,
                scheduled_dates: Array.from(
                  new Set([...(item.scheduled_dates || []), addedDate]),
                ).sort(),
              }
            : item,
        ),
      );
      setNotice(`Added "${addedOpportunity.title}" to your calendar.`);
      setCalendarOpportunity(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Could not add this to the calendar.",
      );
    } finally {
      setAddingToCalendar(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="flex flex-col gap-8 text-on-surface"
    >
      <div className="flex flex-col gap-1">
        <h1 className="font-playfair text-3xl font-bold text-primary">
          Content Opportunities
        </h1>
        <p className="text-sm font-literata text-on-surface-variant max-w-2xl">
          Turn audience evidence into specific things to make next. Every
          opportunity below is linked to the insights and comments that
          support it.
        </p>
      </div>

      {/* Generation card */}
      <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-3xl p-6 md:p-8 shadow-sm flex flex-col gap-5">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#0b3d2e]/10 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div className="flex flex-col">
            <h2 className="font-playfair text-lg font-bold text-primary">
              Generate from an analysis
            </h2>
            <p className="text-xs font-literata text-on-surface-variant mt-0.5">
              Pick one analyzed video. We use its questions, pain points,
              themes, and representative comments as evidence.
            </p>
          </div>
        </div>

        {loadingSources ? (
          <div className="h-11 rounded-xl bg-surface-container animate-pulse" />
        ) : sources.length === 0 ? (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-surface-container-low border border-outline-variant/10 rounded-2xl p-5">
            <div className="flex items-center gap-3">
              <Film className="w-5 h-5 text-on-surface-variant/50" />
              <div className="flex flex-col">
                <span className="font-literata text-sm font-semibold text-primary">
                  No analyzed videos yet
                </span>
                <span className="text-xs font-literata text-on-surface-variant">
                  Analyze a video from your library to create opportunities.
                </span>
              </div>
            </div>
            <Link
              href="/dashboard/videos"
              className="px-5 py-2.5 rounded-full bg-primary text-on-primary text-xs font-semibold font-literata hover:bg-primary-container transition text-center"
            >
              Go to Videos
            </Link>
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row gap-3">
            <VideoSourceSelect
              sources={sources}
              value={selectedAnalysisId}
              onChange={setSelectedAnalysisId}
            />
            <button
              onClick={() => handleGenerate(false)}
              disabled={generating || !selectedAnalysisId}
              className="px-6 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition shadow-sm flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer whitespace-nowrap"
            >
              {generating ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Generate opportunities</span>
                </>
              )}
            </button>
            <button
              onClick={() => handleGenerate(true)}
              disabled={generating || !selectedAnalysisId}
              title="Generate a fresh set. Saved opportunities are kept."
              className="px-5 py-2.5 rounded-full border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container text-xs font-semibold font-literata transition flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer whitespace-nowrap"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${generating ? "animate-spin" : ""}`} />
              <span>Regenerate</span>
            </button>
          </div>
        )}

        {selectedSource && (
          <span className="text-[10px] font-literata text-on-surface-variant/70">
            Source: {selectedSource.video_title} · {selectedSource.platform} ·{" "}
            {selectedSource.comments_analyzed} comments analyzed
          </span>
        )}
      </div>

      {error && (
        <div className="p-4 bg-amber-50 border border-amber-200 text-amber-900 rounded-2xl flex items-start gap-2 font-literata text-xs">
          <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto font-bold p-0.5 cursor-pointer"
            aria-label="Dismiss error"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {notice && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl flex items-center gap-2 font-literata text-xs">
          <Check className="w-4 h-4" />
          <span>{notice}</span>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        {(
          [
            ["all", "All"],
            ["new", "New"],
            ["saved", "Saved"],
            ["dismissed", "Dismissed"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setStatusFilter(key)}
            className={cn(
              "px-4 py-1.5 rounded-full text-xs font-semibold font-literata border transition cursor-pointer",
              statusFilter === key
                ? "bg-primary text-on-primary border-primary"
                : "border-outline-variant/20 text-on-surface-variant hover:bg-surface-container",
            )}
          >
            {label}
            <span className="ml-1.5 opacity-70">({counts[key]})</span>
          </button>
        ))}
      </div>

      {/* List */}
      {loadingOpportunities ? (
        <div className="grid md:grid-cols-2 gap-5">
          {[1, 2].map((i) => (
            <div
              key={i}
              className="h-72 bg-surface-container rounded-3xl animate-pulse"
            />
          ))}
        </div>
      ) : visibleOpportunities.length === 0 ? (
        <div className="flex flex-col items-center gap-4 py-20 text-center max-w-md mx-auto">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <Lightbulb className="w-7 h-7 text-primary" />
          </div>
          <h2 className="font-playfair text-xl font-bold text-primary">
            {opportunities.length === 0
              ? "No opportunities yet"
              : "Nothing in this filter"}
          </h2>
          <p className="font-literata text-sm text-on-surface-variant leading-relaxed">
            {opportunities.length === 0
              ? "Choose an analyzed video above and generate evidence-backed content opportunities."
              : "Try another status filter to see the rest of your opportunities."}
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-5">
          {visibleOpportunities.map((opportunity) => {
            const isDismissed = opportunity.status === "dismissed";
            return (
              <div
                key={opportunity.id}
                className={cn(
                  "relative bg-white border border-outline-variant/10 rounded-3xl p-6 shadow-sm flex flex-col gap-5 transition",
                  isDismissed ? "opacity-50" : "hover:shadow-md",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        "text-[9px] font-bold tracking-wider uppercase px-2 py-0.5 rounded-full border",
                        PRIORITY_STYLES[opportunity.priority] ||
                          PRIORITY_STYLES.medium,
                      )}
                    >
                      {opportunity.priority} priority
                    </span>
                    <span
                      className={cn(
                        "text-[9px] font-bold tracking-wider uppercase px-2 py-0.5 rounded-full border",
                        STATUS_STYLES[opportunity.status] || STATUS_STYLES.new,
                      )}
                    >
                      {opportunity.status}
                    </span>
                  </div>
                  <Target className="w-4 h-4 text-on-surface-variant/30 flex-shrink-0" />
                </div>

                <div className="flex flex-col gap-2">
                  <h3
                    className={cn(
                      "font-playfair text-lg font-bold leading-snug",
                      isDismissed
                        ? "line-through text-on-surface-variant"
                        : "text-primary",
                    )}
                  >
                    {opportunity.title}
                  </h3>
                  <p className="text-xs font-literata text-on-surface-variant leading-relaxed">
                    {opportunity.rationale}
                  </p>
                  {opportunity.suggested_angle && (
                    <p className="text-xs font-literata text-on-surface leading-relaxed bg-surface-container-low rounded-xl px-3 py-2">
                      <span className="font-semibold">Angle:</span>{" "}
                      {opportunity.suggested_angle}
                    </p>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-2 text-[10px] font-literata text-on-surface-variant">
                  <span className="px-2 py-1 rounded-full bg-surface-container border border-outline-variant/10 capitalize">
                    {opportunity.suggested_format}
                  </span>
                  <span className="px-2 py-1 rounded-full bg-surface-container border border-outline-variant/10">
                    {LENGTH_LABELS[opportunity.suggested_length] ||
                      opportunity.suggested_length}
                  </span>
                  {opportunity.source_video_title &&
                    (opportunity.source_video_id ? (
                      <Link
                        href={`/dashboard/videos/${opportunity.source_video_id}`}
                        className="flex items-center gap-1 hover:text-primary transition"
                      >
                        <Film className="w-3 h-3" />
                        {opportunity.source_video_title}
                      </Link>
                    ) : (
                      <span className="flex items-center gap-1">
                        <Film className="w-3 h-3" />
                        {opportunity.source_video_title}
                      </span>
                    ))}
                </div>

                <div className="flex flex-col gap-2 border-t border-outline-variant/10 pt-4">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant/70 flex items-center gap-1">
                    <Quote className="w-3 h-3" />
                    Audience evidence ({opportunity.evidence.length})
                  </span>
                  {opportunity.evidence.length === 0 ? (
                    <span className="text-xs font-literata text-amber-700">
                      No direct evidence was attached to this suggestion.
                    </span>
                  ) : (
                    <div className="flex flex-col gap-2">
                      {opportunity.evidence.slice(0, 3).map((evidence) => (
                        <blockquote
                          key={evidence.id}
                          className="text-xs font-literata text-on-surface-variant leading-relaxed border-l-2 border-primary/20 pl-3"
                        >
                          <span className="block text-[9px] font-bold uppercase tracking-wider text-on-surface-variant/50 mb-0.5">
                            {evidenceLabel(evidence)}
                          </span>
                          {evidence.quote || "Source no longer available."}
                        </blockquote>
                      ))}
                      {opportunity.evidence.length > 3 && (
                        <span className="text-[10px] font-literata text-on-surface-variant/60">
                          +{opportunity.evidence.length - 3} more evidence items
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2 mt-auto pt-4 border-t border-outline-variant/10">
                  {isDismissed ? (
                    <button
                      onClick={() => handleStatus(opportunity, "new")}
                      className="text-xs font-semibold font-literata text-primary hover:underline cursor-pointer"
                    >
                      Restore
                    </button>
                  ) : (
                    <>
                      <button
                        onClick={() =>
                          handleStatus(
                            opportunity,
                            opportunity.status === "saved" ? "new" : "saved",
                          )
                        }
                        className={cn(
                          "flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold font-literata border transition cursor-pointer",
                          opportunity.status === "saved"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-surface-container text-on-surface-variant border-outline-variant/20 hover:bg-emerald-50 hover:text-emerald-700",
                        )}
                      >
                        <Check className="w-3 h-3" />
                        {opportunity.status === "saved" ? "Saved" : "Save"}
                      </button>
                      <button
                        onClick={() => handleStatus(opportunity, "dismissed")}
                        className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold font-literata border border-outline-variant/20 text-on-surface-variant hover:bg-rose-50 hover:text-rose-700 transition cursor-pointer"
                      >
                        <X className="w-3 h-3" />
                        Dismiss
                      </button>
                      {opportunity.is_scheduled ? (
                        <Link
                          href="/dashboard/calendar"
                          title={
                            opportunity.scheduled_dates.length > 0
                              ? `Scheduled for ${opportunity.scheduled_dates
                                  .map(formatScheduledDate)
                                  .join(", ")}`
                              : "Already on your calendar"
                          }
                          className="ml-auto flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold font-literata border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition"
                        >
                          <Calendar className="w-3 h-3" />
                          On calendar
                        </Link>
                      ) : (
                        <button
                          onClick={() => openCalendarDialog(opportunity)}
                          className="ml-auto flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold font-literata border border-primary/20 text-primary hover:bg-primary/5 transition cursor-pointer"
                        >
                          <Calendar className="w-3 h-3" />
                          Add to calendar
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="flex items-center justify-between text-[10px] font-literata text-on-surface-variant/60 border-t border-outline-variant/10 pt-4">
        <span className="flex items-center gap-1">
          <MessageSquare className="w-3 h-3" />
          Opportunities are generated from completed comment analyses only.
        </span>
        <button
          onClick={() => {
            fetchSources();
            fetchOpportunities();
          }}
          className="flex items-center gap-1 hover:text-primary transition cursor-pointer"
        >
          <RefreshCw className="w-3 h-3" />
          Refresh
        </button>
      </div>

      {/* Add to calendar dialog */}
      {calendarOpportunity && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-primary/20 backdrop-blur-sm"
            onClick={() => !addingToCalendar && setCalendarOpportunity(null)}
          />
          <div className="relative w-full max-w-md bg-surface-container-lowest rounded-3xl shadow-2xl p-6 flex flex-col gap-5">
            <div className="flex items-start justify-between gap-3">
              <div className="flex flex-col">
                <h2 className="font-playfair text-lg font-bold text-primary">
                  Add to calendar
                </h2>
                <p className="text-xs font-literata text-on-surface-variant mt-1">
                  {calendarOpportunity.title}
                </p>
              </div>
              <button
                onClick={() => !addingToCalendar && setCalendarOpportunity(null)}
                className="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container transition cursor-pointer"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  Date
                </span>
                <input
                  type="date"
                  value={calendarDate}
                  onChange={(event) => setCalendarDate(event.target.value)}
                  className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  Time (optional)
                </span>
                <input
                  type="time"
                  value={calendarTime}
                  onChange={(event) => setCalendarTime(event.target.value)}
                  className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </label>
            </div>

            <p className="text-[10px] font-literata text-on-surface-variant/70">
              The topic, format, length, and angle are copied from the opportunity.
              You can edit them after adding.
            </p>

            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setCalendarOpportunity(null)}
                disabled={addingToCalendar}
                className="px-5 py-2.5 rounded-full border border-outline-variant/30 text-on-surface-variant text-xs font-semibold font-literata hover:bg-surface-container transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleAddToCalendar}
                disabled={addingToCalendar}
                className="px-5 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition disabled:opacity-50 flex items-center gap-2 cursor-pointer"
              >
                {addingToCalendar && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {addingToCalendar ? "Adding..." : "Add to calendar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
