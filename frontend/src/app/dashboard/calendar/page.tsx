"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock,
  Film,
  FileText,
  Loader2,
  Plus,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { authedFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

type CalendarStatus = "idea" | "planned" | "in_progress" | "ready" | "published";

interface CalendarItem {
  id: string;
  opportunity_id: string | null;
  title: string;
  angle: string;
  notes: string;
  content_context: string;
  format: string;
  length: string;
  platform: string;
  scheduled_date: string;
  scheduled_time: string | null;
  status: CalendarStatus;
  created_at: string;
  updated_at: string;
}

interface Opportunity {
  id: string;
  title: string;
  suggested_format: string;
  suggested_length: string;
  suggested_angle: string;
  priority: string;
  status: "new" | "saved" | "dismissed";
  source_video_title: string | null;
}

interface ItemForm {
  title: string;
  angle: string;
  notes: string;
  content_context: string;
  format: string;
  length: string;
  platform: string;
  scheduled_date: string;
  scheduled_time: string;
  status: CalendarStatus;
}

const FORMATS = ["tutorial", "explainer", "comparison", "faq", "demo", "opinion"];
const LENGTHS = [
  { value: "long_form", label: "Long-form" },
  { value: "short", label: "Short" },
];
const PLATFORMS = ["youtube"];
const STATUS_ORDER: CalendarStatus[] = [
  "idea",
  "planned",
  "in_progress",
  "ready",
  "published",
];

const STATUS_CONFIG: Record<
  CalendarStatus,
  { label: string; color: string; dot: string }
> = {
  idea: {
    label: "Idea",
    color: "bg-slate-100 text-slate-600 border-slate-200",
    dot: "bg-slate-400",
  },
  planned: {
    label: "Planned",
    color: "bg-amber-50 text-amber-700 border-amber-200",
    dot: "bg-amber-400",
  },
  in_progress: {
    label: "In Progress",
    color: "bg-sky-50 text-sky-700 border-sky-200",
    dot: "bg-sky-400",
  },
  ready: {
    label: "Ready",
    color: "bg-violet-50 text-violet-700 border-violet-200",
    dot: "bg-violet-400",
  },
  published: {
    label: "Published",
    color: "bg-emerald-50 text-emerald-700 border-emerald-200",
    dot: "bg-emerald-400",
  },
};

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const DAY_LABELS_LONG = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
const CADENCE_DAY_ORDER = [0, 2, 4, 1, 3, 5, 6];

function toIsoDate(value: Date): string {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function fromIsoDate(value: string): Date {
  return new Date(`${value}T00:00:00`);
}

function mondayOf(value: Date): string {
  const copy = new Date(value);
  const weekday = (copy.getDay() + 6) % 7; // 0 = Monday
  copy.setDate(copy.getDate() - weekday);
  return toIsoDate(copy);
}

function addDays(value: string, days: number): string {
  const date = fromIsoDate(value);
  date.setDate(date.getDate() + days);
  return toIsoDate(date);
}

function formatWeekRange(start: string, end: string): string {
  const startDate = fromIsoDate(start);
  const endDate = fromIsoDate(end);
  const sameMonth = startDate.getMonth() === endDate.getMonth();
  const startLabel = startDate.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  const endLabel = endDate.toLocaleDateString(undefined, {
    month: sameMonth ? undefined : "short",
    day: "numeric",
    year: "numeric",
  });
  return `${startLabel} – ${endLabel}`;
}

function formatTime(value: string | null): string {
  if (!value) return "";
  const [hour, minute] = value.split(":");
  const date = new Date();
  date.setHours(Number(hour), Number(minute), 0, 0);
  return date.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

function emptyForm(date: string): ItemForm {
  return {
    title: "",
    angle: "",
    notes: "",
    content_context: "",
    format: "tutorial",
    length: "long_form",
    platform: "youtube",
    scheduled_date: date,
    scheduled_time: "",
    status: "idea",
  };
}

export default function CalendarPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const [weekStart, setWeekStart] = useState(() => mondayOf(new Date()));
  const [items, setItems] = useState<CalendarItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Editor
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<CalendarItem | null>(null);
  const [form, setForm] = useState<ItemForm>(() => emptyForm(mondayOf(new Date())));
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Planner
  const [planOpen, setPlanOpen] = useState(false);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [selectedOpportunityIds, setSelectedOpportunityIds] = useState<string[]>([]);
  const [planDays, setPlanDays] = useState<number[]>([0, 2, 4]);
  const [planning, setPlanning] = useState(false);
  const [loadingOpportunities, setLoadingOpportunities] = useState(false);

  const fetchWeek = useCallback(
    async (start: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await authedFetch(
          `${apiUrl}/api/v1/content/calendar?week_start=${start}`,
        );
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data?.detail?.message || "Could not load your calendar.");
        }
        setItems(data.data || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load your calendar.");
      } finally {
        setLoading(false);
      }
    },
    [apiUrl],
  );

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    fetchWeek(weekStart);
  }, [fetchWeek, weekStart]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, index) => addDays(weekStart, index)),
    [weekStart],
  );

  const itemsByDate = useMemo(() => {
    const grouped: Record<string, CalendarItem[]> = {};
    for (const item of items) {
      grouped[item.scheduled_date] = grouped[item.scheduled_date] || [];
      grouped[item.scheduled_date].push(item);
    }
    return grouped;
  }, [items]);

  const weekEnd = addDays(weekStart, 6);

  const openCreate = (date?: string) => {
    setEditingItem(null);
    setForm(emptyForm(date || weekStart));
    setEditorOpen(true);
    setError(null);
  };

  const openEdit = (item: CalendarItem) => {
    setEditingItem(item);
    setForm({
      title: item.title,
      angle: item.angle,
      notes: item.notes,
      content_context: item.content_context,
      format: item.format,
      length: item.length,
      platform: item.platform,
      scheduled_date: item.scheduled_date,
      scheduled_time: item.scheduled_time ? item.scheduled_time.slice(0, 5) : "",
      status: item.status,
    });
    setEditorOpen(true);
    setError(null);
  };

  const closeEditor = () => {
    if (saving || deleting) return;
    setEditorOpen(false);
    setEditingItem(null);
  };

  const handleSave = async () => {
    if (!form.title.trim()) {
      setError("Give the calendar item a title.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const body = {
        title: form.title.trim(),
        angle: form.angle,
        notes: form.notes,
        content_context: form.content_context,
        format: form.format,
        length: form.length,
        platform: form.platform,
        scheduled_date: form.scheduled_date,
        scheduled_time: form.scheduled_time || null,
        status: form.status,
      };
      const res = await authedFetch(
        editingItem
          ? `${apiUrl}/api/v1/content/calendar/items/${editingItem.id}`
          : `${apiUrl}/api/v1/content/calendar/items`,
        {
          method: editingItem ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail?.message || "Could not save the calendar item.");
      }
      setEditorOpen(false);
      setEditingItem(null);
      setNotice(editingItem ? "Calendar item updated." : "Added to your calendar.");
      await fetchWeek(weekStart);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the calendar item.");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!editingItem) return;
    setDeleting(true);
    setError(null);
    try {
      const res = await authedFetch(
        `${apiUrl}/api/v1/content/calendar/items/${editingItem.id}`,
        { method: "DELETE" },
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail?.message || "Could not delete the calendar item.");
      }
      setEditorOpen(false);
      setEditingItem(null);
      setNotice("Removed from your calendar.");
      await fetchWeek(weekStart);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete the calendar item.");
    } finally {
      setDeleting(false);
    }
  };

  const openPlanner = async () => {
    setPlanOpen(true);
    setError(null);
    setLoadingOpportunities(true);
    try {
      const [oppRes, styleRes] = await Promise.all([
        authedFetch(`${apiUrl}/api/v1/content/opportunities?limit=100`),
        authedFetch(`${apiUrl}/api/v1/content/style`),
      ]);
      const data = await oppRes.json().catch(() => ({}));
      if (!oppRes.ok) {
        throw new Error(data?.detail?.message || "Could not load opportunities.");
      }
      const available: Opportunity[] = (data.data || []).filter(
        (item: Opportunity) => item.status !== "dismissed",
      );
      setOpportunities(available);
      setSelectedOpportunityIds(
        available.filter((item) => item.status === "saved").map((item) => item.id),
      );

      // Use the creator's saved cadence as the starting point. They can still
      // override the days in this dialog.
      if (styleRes.ok) {
        const style = await styleRes.json().catch(() => ({}));
        const cadence = Math.max(
          1,
          Math.min(7, Number(style?.posting_cadence) || 3),
        );
        setPlanDays(CADENCE_DAY_ORDER.slice(0, cadence).sort((a, b) => a - b));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load opportunities.");
    } finally {
      setLoadingOpportunities(false);
    }
  };

  const toggleOpportunity = (id: string) => {
    setSelectedOpportunityIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  };

  const togglePlanDay = (day: number) => {
    setPlanDays((current) =>
      current.includes(day)
        ? current.filter((item) => item !== day)
        : [...current, day].sort(),
    );
  };

  const handlePlan = async () => {
    if (selectedOpportunityIds.length === 0) {
      setError("Select at least one opportunity to plan.");
      return;
    }
    if (planDays.length === 0) {
      setError("Select at least one posting day.");
      return;
    }
    setPlanning(true);
    setError(null);
    try {
      const res = await authedFetch(`${apiUrl}/api/v1/content/calendar/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          week_start: weekStart,
          opportunity_ids: selectedOpportunityIds,
          days: planDays,
          platform: "youtube",
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data?.detail?.message || "Could not plan the week.");
      }
      setPlanOpen(false);
      setNotice(
        data.planned > 0
          ? `Planned ${data.planned} item${data.planned === 1 ? "" : "s"} for the week.`
          : "Those opportunities are already on this week's calendar.",
      );
      await fetchWeek(weekStart);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not plan the week.");
    } finally {
      setPlanning(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="flex flex-col gap-6 text-on-surface"
    >
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h1 className="font-playfair text-3xl font-bold text-primary">
            Content Calendar
          </h1>
          <p className="text-sm font-literata text-on-surface-variant max-w-2xl">
            Turn saved opportunities into a weekly plan. Everything is editable —
            move items, change formats, and update statuses as you go.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={openPlanner}
            className="px-5 py-2.5 rounded-full border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container text-xs font-semibold font-literata transition flex items-center gap-2 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Plan week
          </button>
          <button
            onClick={() => openCreate()}
            className="px-5 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition shadow-sm flex items-center gap-2 cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            Add item
          </button>
        </div>
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

      {/* Week navigation */}
      <div className="flex items-center justify-between gap-3 bg-white/70 border border-outline-variant/10 rounded-2xl px-4 py-3 shadow-sm">
        <button
          onClick={() => setWeekStart(addDays(weekStart, -7))}
          className="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container transition cursor-pointer"
          aria-label="Previous week"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-3">
          <CalendarDays className="w-4 h-4 text-primary" />
          <span className="font-playfair text-base font-bold text-primary">
            {formatWeekRange(weekStart, weekEnd)}
          </span>
          <button
            onClick={() => setWeekStart(mondayOf(new Date()))}
            className="text-[11px] font-semibold font-literata text-on-surface-variant hover:text-primary transition cursor-pointer"
          >
            Today
          </button>
        </div>
        <button
          onClick={() => setWeekStart(addDays(weekStart, 7))}
          className="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container transition cursor-pointer"
          aria-label="Next week"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Week grid */}
      {loading ? (
        <div className="grid md:grid-cols-2 xl:grid-cols-7 gap-3">
          {Array.from({ length: 7 }).map((_, index) => (
            <div
              key={index}
              className="h-56 bg-surface-container rounded-2xl animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-7 gap-3 items-start">
          {days.map((day, index) => {
            const dayItems = itemsByDate[day] || [];
            const isToday = day === toIsoDate(new Date());
            return (
              <div
                key={day}
                className={cn(
                  "flex flex-col gap-2 rounded-2xl border p-2.5 min-h-[180px]",
                  isToday
                    ? "border-primary/30 bg-primary/[0.03]"
                    : "border-outline-variant/10 bg-white/60",
                )}
              >
                <div className="flex items-center justify-between px-1">
                  <div className="flex flex-col">
                    <span className="text-[9px] font-bold uppercase tracking-wider text-on-surface-variant/60">
                      {DAY_LABELS[index]}
                    </span>
                    <span
                      className={cn(
                        "font-playfair text-lg font-bold leading-none",
                        isToday ? "text-primary" : "text-on-surface",
                      )}
                    >
                      {fromIsoDate(day).getDate()}
                    </span>
                  </div>
                  <button
                    onClick={() => openCreate(day)}
                    className="p-1.5 rounded-lg text-on-surface-variant/40 hover:text-primary hover:bg-surface-container transition cursor-pointer"
                    aria-label={`Add item on ${DAY_LABELS_LONG[index]}`}
                  >
                    <Plus className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex flex-col gap-2">
                  {dayItems.length === 0 ? (
                    <span className="text-[10px] font-literata text-on-surface-variant/35 italic px-1 py-4 text-center">
                      No content
                    </span>
                  ) : (
                    dayItems.map((item) => {
                      const config = STATUS_CONFIG[item.status] || STATUS_CONFIG.idea;
                      return (
                        <button
                          key={item.id}
                          onClick={() => openEdit(item)}
                          className="text-left bg-surface-container-lowest border border-outline-variant/10 rounded-xl p-3 shadow-sm hover:shadow transition flex flex-col gap-2 cursor-pointer"
                        >
                          <div className="flex items-center gap-1.5">
                            <span className={cn("w-1.5 h-1.5 rounded-full", config.dot)} />
                            <span
                              className={cn(
                                "text-[8px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full border",
                                config.color,
                              )}
                            >
                              {config.label}
                            </span>
                          </div>
                          <span className="font-literata text-xs font-semibold text-primary leading-snug line-clamp-2">
                            {item.title}
                          </span>
                          <div className="flex flex-wrap items-center gap-1.5 text-[9px] font-literata text-on-surface-variant/70">
                            <span className="px-1.5 py-0.5 rounded-full bg-surface-container capitalize">
                              {item.format}
                            </span>
                            <span className="px-1.5 py-0.5 rounded-full bg-surface-container">
                              {item.length === "short" ? "Short" : "Long-form"}
                            </span>
                            <span className="px-1.5 py-0.5 rounded-full bg-surface-container capitalize">
                              {item.platform}
                            </span>
                          </div>
                          {item.scheduled_time && (
                            <span className="flex items-center gap-1 text-[9px] font-literata text-on-surface-variant/60">
                              <Clock className="w-2.5 h-2.5" />
                              {formatTime(item.scheduled_time)}
                            </span>
                          )}
                        </button>
                      );
                    })
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {items.length === 0 && !loading && (
        <div className="flex flex-col items-center gap-4 py-16 text-center max-w-md mx-auto">
          <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
            <CalendarDays className="w-7 h-7 text-primary" />
          </div>
          <h2 className="font-playfair text-xl font-bold text-primary">
            This week is open
          </h2>
          <p className="font-literata text-sm text-on-surface-variant leading-relaxed">
            Add an item manually, or plan the week from your saved content
            opportunities.
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={openPlanner}
              className="px-5 py-2.5 rounded-full bg-primary text-on-primary text-xs font-semibold font-literata hover:bg-primary-container transition"
            >
              Plan from opportunities
            </button>
            <Link
              href="/dashboard/opportunities"
              className="px-5 py-2.5 rounded-full border border-outline-variant/30 text-on-surface-variant text-xs font-semibold font-literata hover:bg-surface-container transition"
            >
              View opportunities
            </Link>
          </div>
        </div>
      )}

      {/* Editor drawer */}
      {editorOpen && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div
            className="absolute inset-0 bg-primary/20 backdrop-blur-sm"
            onClick={closeEditor}
          />
          <div className="relative w-full max-w-md h-full bg-surface-container-lowest shadow-2xl overflow-y-auto flex flex-col">
            <div className="flex items-center justify-between px-6 py-5 border-b border-outline-variant/10">
              <div className="flex flex-col">
                <h2 className="font-playfair text-lg font-bold text-primary">
                  {editingItem ? "Edit calendar item" : "New calendar item"}
                </h2>
                <span className="text-[10px] font-literata text-on-surface-variant">
                  {editingItem
                    ? "Changes save to your calendar."
                    : "Add a planned piece of content."}
                </span>
              </div>
              <button
                onClick={closeEditor}
                className="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container transition cursor-pointer"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-col gap-4 p-6 flex-1">
              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  Title
                </span>
                <input
                  value={form.title}
                  onChange={(event) => setForm({ ...form, title: event.target.value })}
                  placeholder="e.g. Camera pricing breakdown"
                  className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  Angle
                </span>
                <textarea
                  value={form.angle}
                  onChange={(event) => setForm({ ...form, angle: event.target.value })}
                  rows={2}
                  placeholder="How you want to approach it"
                  className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                />
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                    Format
                  </span>
                  <select
                    value={form.format}
                    onChange={(event) => setForm({ ...form, format: event.target.value })}
                    className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary capitalize"
                  >
                    {FORMATS.map((format) => (
                      <option key={format} value={format}>
                        {format}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                    Length
                  </span>
                  <select
                    value={form.length}
                    onChange={(event) => setForm({ ...form, length: event.target.value })}
                    className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    {LENGTHS.map((length) => (
                      <option key={length.value} value={length.value}>
                        {length.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                    Date
                  </span>
                  <input
                    type="date"
                    value={form.scheduled_date}
                    onChange={(event) =>
                      setForm({ ...form, scheduled_date: event.target.value })
                    }
                    className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                    Time (optional)
                  </span>
                  <input
                    type="time"
                    value={form.scheduled_time}
                    onChange={(event) =>
                      setForm({ ...form, scheduled_time: event.target.value })
                    }
                    className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </label>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                    Platform
                  </span>
                  <select
                    value={form.platform}
                    onChange={(event) => setForm({ ...form, platform: event.target.value })}
                    className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary capitalize"
                  >
                    {PLATFORMS.map((platform) => (
                      <option key={platform} value={platform}>
                        {platform}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                    Status
                  </span>
                  <select
                    value={form.status}
                    onChange={(event) =>
                      setForm({
                        ...form,
                        status: event.target.value as CalendarStatus,
                      })
                    }
                    className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary"
                  >
                    {STATUS_ORDER.map((status) => (
                      <option key={status} value={status}>
                        {STATUS_CONFIG[status].label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  Notes
                </span>
                <textarea
                  value={form.notes}
                  onChange={(event) => setForm({ ...form, notes: event.target.value })}
                  rows={3}
                  placeholder="Anything to remember while creating this"
                  className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary resize-none"
                />
              </label>

              <label className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
                  Video context / transcript notes
                </span>
                <textarea
                  value={form.content_context}
                  onChange={(event) =>
                    setForm({ ...form, content_context: event.target.value })
                  }
                  rows={4}
                  placeholder="Paste the transcript, outline, or key facts the script should follow. Used when the video transcript is unavailable."
                  className="px-3 py-2.5 rounded-xl border border-outline-variant/30 text-sm font-literata bg-white focus:outline-none focus:ring-1 focus:ring-primary resize-y"
                />
              </label>

              {editingItem && (
                <Link
                  href={`/dashboard/calendar/items/${editingItem.id}/script`}
                  className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border border-primary/20 text-primary text-xs font-semibold font-literata hover:bg-primary/5 transition"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Open script / brief
                </Link>
              )}

              {editingItem?.opportunity_id && (
                <Link
                  href="/dashboard/opportunities"
                  className="text-[10px] font-literata text-primary hover:underline"
                >
                  View the source opportunity
                </Link>
              )}
            </div>

            <div className="p-6 border-t border-outline-variant/10 flex items-center gap-3">
              {editingItem && (
                <button
                  onClick={handleDelete}
                  disabled={deleting || saving}
                  className="p-2.5 rounded-xl border border-rose-200 text-rose-600 hover:bg-rose-50 transition disabled:opacity-50 cursor-pointer"
                  aria-label="Delete calendar item"
                >
                  {deleting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              )}
              <button
                onClick={handleSave}
                disabled={saving || deleting}
                className="flex-1 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition disabled:opacity-50 flex items-center justify-center gap-2 cursor-pointer"
              >
                {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {saving ? "Saving..." : editingItem ? "Save changes" : "Add to calendar"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Planner modal */}
      {planOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-primary/20 backdrop-blur-sm"
            onClick={() => !planning && setPlanOpen(false)}
          />
          <div className="relative w-full max-w-2xl max-h-[85vh] bg-surface-container-lowest rounded-3xl shadow-2xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5 border-b border-outline-variant/10">
              <div className="flex flex-col">
                <h2 className="font-playfair text-lg font-bold text-primary">
                  Plan this week
                </h2>
                <span className="text-[10px] font-literata text-on-surface-variant">
                  Deterministically place selected opportunities on your posting days.
                </span>
              </div>
              <button
                onClick={() => !planning && setPlanOpen(false)}
                className="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container transition cursor-pointer"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex flex-col gap-5">
              <div className="flex flex-col gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                  Posting days
                </span>
                <div className="flex flex-wrap gap-2">
                  {DAY_LABELS.map((label, index) => {
                    const active = planDays.includes(index);
                    return (
                      <button
                        key={label}
                        onClick={() => togglePlanDay(index)}
                        className={cn(
                          "px-3 py-1.5 rounded-full text-xs font-semibold font-literata border transition cursor-pointer",
                          active
                            ? "bg-primary text-on-primary border-primary"
                            : "border-outline-variant/20 text-on-surface-variant hover:bg-surface-container",
                        )}
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                    Opportunities
                  </span>
                  <span className="text-[10px] font-literata text-on-surface-variant/60">
                    {selectedOpportunityIds.length} selected
                  </span>
                </div>

                {loadingOpportunities ? (
                  <div className="h-40 rounded-2xl bg-surface-container animate-pulse" />
                ) : opportunities.length === 0 ? (
                  <div className="flex flex-col items-center gap-3 py-10 text-center bg-surface-container-low rounded-2xl">
                    <Film className="w-7 h-7 text-on-surface-variant/30" />
                    <p className="text-xs font-literata text-on-surface-variant max-w-sm">
                      No saved or new opportunities yet. Generate some from an
                      analysis first.
                    </p>
                    <Link
                      href="/dashboard/opportunities"
                      className="text-xs font-semibold font-literata text-primary hover:underline"
                    >
                      Go to Opportunities
                    </Link>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2 max-h-72 overflow-y-auto pr-1">
                    {opportunities.map((opportunity) => {
                      const selected = selectedOpportunityIds.includes(opportunity.id);
                      return (
                        <button
                          key={opportunity.id}
                          onClick={() => toggleOpportunity(opportunity.id)}
                          className={cn(
                            "flex items-start gap-3 text-left p-3 rounded-xl border transition cursor-pointer",
                            selected
                              ? "border-primary/40 bg-primary/[0.04]"
                              : "border-outline-variant/15 hover:bg-surface-container",
                          )}
                        >
                          <span
                            className={cn(
                              "mt-0.5 w-4 h-4 rounded border flex items-center justify-center flex-shrink-0",
                              selected
                                ? "bg-primary border-primary text-on-primary"
                                : "border-outline-variant/40",
                            )}
                          >
                            {selected && <Check className="w-3 h-3" />}
                          </span>
                          <span className="flex flex-col gap-1">
                            <span className="font-literata text-sm font-semibold text-primary">
                              {opportunity.title}
                            </span>
                            <span className="text-[10px] font-literata text-on-surface-variant">
                              {opportunity.suggested_format} ·{" "}
                              {opportunity.suggested_length === "short"
                                ? "Short"
                                : "Long-form"}
                              {opportunity.source_video_title
                                ? ` · ${opportunity.source_video_title}`
                                : ""}
                            </span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="px-6 py-4 border-t border-outline-variant/10 flex items-center justify-end gap-3">
              <button
                onClick={() => setPlanOpen(false)}
                disabled={planning}
                className="px-5 py-2.5 rounded-full border border-outline-variant/30 text-on-surface-variant text-xs font-semibold font-literata hover:bg-surface-container transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handlePlan}
                disabled={planning || selectedOpportunityIds.length === 0}
                className="px-5 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition disabled:opacity-50 flex items-center gap-2 cursor-pointer"
              >
                {planning && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                {planning ? "Planning..." : "Plan week"}
              </button>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}
