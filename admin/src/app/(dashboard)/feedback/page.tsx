"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  Search,
  Star,
} from "lucide-react";
import { getJson, patchJson } from "@/lib/http";
import { cn, formatDate } from "@/lib/utils";

interface FeedbackRow {
  id: string;
  user_id: string | null;
  email: string | null;
  rating: number | null;
  category: string;
  message: string;
  page: string | null;
  status: string;
  created_at: string;
}

interface PaginatedFeedback {
  data: FeedbackRow[];
  pagination: { page: number; limit: number; total: number; pages: number };
}

const CATEGORY_OPTIONS = ["", "bug", "idea", "praise", "other"];
const STATUS_OPTIONS = [
  { label: "All", value: "" },
  { label: "New", value: "new" },
  { label: "Resolved", value: "resolved" },
];

const CATEGORY_STYLES: Record<string, string> = {
  bug: "border-red-200 text-red-700 bg-red-50",
  idea: "border-sky-200 text-sky-700 bg-sky-50",
  praise: "border-emerald-200 text-emerald-700 bg-emerald-50",
  other: "border-outline-variant/30 text-on-surface-variant",
};

export default function FeedbackPage() {
  const [rows, setRows] = useState<FeedbackRow[]>([]);
  const [pagination, setPagination] =
    useState<PaginatedFeedback["pagination"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debounced, category, status]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(page), limit: "20" });
      if (debounced) params.set("search", debounced);
      if (category) params.set("category", category);
      if (status) params.set("status", status);
      const data = await getJson<PaginatedFeedback>(
        `/admin/feedback?${params.toString()}`,
      );
      setRows(data.data);
      setPagination(data.pagination);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load feedback.");
    } finally {
      setLoading(false);
    }
  }, [page, debounced, category, status]);

  useEffect(() => {
    load();
  }, [load]);

  const toggleStatus = async (row: FeedbackRow) => {
    const next = row.status === "resolved" ? "new" : "resolved";
    setUpdatingId(row.id);
    try {
      await patchJson(`/admin/feedback/${row.id}`, { status: next });
      setRows((prev) =>
        prev.map((r) => (r.id === row.id ? { ...r, status: next } : r)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update feedback.");
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-6 text-on-surface"
    >
      <div className="flex flex-col">
        <h1 className="font-playfair text-3xl font-bold text-primary">Feedback</h1>
        <p className="text-on-surface-variant font-literata text-sm mt-1">
          {pagination
            ? `${pagination.total} submissions`
            : "What creators are telling us."}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-on-surface-variant/60 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search messages or email..."
            className="w-full bg-surface-container-low border border-outline-variant/20 rounded-full py-2 pl-10 pr-4 font-literata text-sm focus:outline-none focus:border-primary/40 focus:bg-surface-container-lowest transition-colors"
          />
        </div>

        <div className="flex items-center gap-1">
          {CATEGORY_OPTIONS.map((c) => (
            <button
              key={c || "all"}
              onClick={() => setCategory(c)}
              className={cn(
                "px-4 py-2 rounded-full text-xs font-literata font-semibold transition-colors capitalize cursor-pointer",
                category === c
                  ? "bg-primary text-on-primary"
                  : "border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container",
              )}
            >
              {c || "All"}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s.label}
              onClick={() => setStatus(s.value)}
              className={cn(
                "px-4 py-2 rounded-full text-xs font-literata font-semibold transition-colors cursor-pointer",
                status === s.value
                  ? "bg-primary text-on-primary"
                  : "border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container",
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <div className="p-6 bg-red-50 border border-red-200 text-red-900 rounded-3xl flex flex-col gap-4 font-literata text-sm">
          <div className="flex items-center gap-2 text-red-700 font-bold">
            <AlertTriangle className="w-5 h-5" />
            <span>Error loading feedback</span>
          </div>
          <p>{error}</p>
          <button
            onClick={load}
            className="px-5 py-2 rounded-full bg-red-700 text-white font-semibold self-start hover:bg-red-800 transition cursor-pointer"
          >
            Retry
          </button>
        </div>
      ) : (
        <div className="bg-white/70 backdrop-blur-md border border-outline-variant/10 rounded-2xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-outline-variant/15 text-[10px] uppercase tracking-wider text-on-surface-variant font-literata">
                  <th className="px-5 py-3 font-medium">User</th>
                  <th className="px-5 py-3 font-medium">Rating</th>
                  <th className="px-5 py-3 font-medium">Category</th>
                  <th className="px-5 py-3 font-medium">Message</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Received</th>
                </tr>
              </thead>
              <tbody>
                {loading
                  ? Array.from({ length: 6 }).map((_, i) => (
                      <tr key={i} className="border-b border-outline-variant/10">
                        <td colSpan={6} className="px-5 py-4">
                          <div className="h-4 bg-surface-container rounded animate-pulse" />
                        </td>
                      </tr>
                    ))
                  : rows.map((r) => (
                      <tr
                        key={r.id}
                        className="border-b border-outline-variant/10 last:border-0 hover:bg-surface-container/30 transition-colors align-top"
                      >
                        <td className="px-5 py-4 font-literata text-sm text-primary whitespace-nowrap">
                          {r.email || "—"}
                        </td>
                        <td className="px-5 py-4 whitespace-nowrap">
                          {r.rating ? (
                            <span className="inline-flex items-center gap-0.5">
                              {Array.from({ length: r.rating }).map((_, i) => (
                                <Star
                                  key={i}
                                  className="w-3.5 h-3.5 text-secondary-container fill-secondary-container"
                                />
                              ))}
                            </span>
                          ) : (
                            <span className="text-on-surface-variant/50 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-5 py-4">
                          <span
                            className={cn(
                              "text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-full border capitalize",
                              CATEGORY_STYLES[r.category] ??
                                "border-outline-variant/30 text-on-surface-variant",
                            )}
                          >
                            {r.category}
                          </span>
                        </td>
                        <td className="px-5 py-4 max-w-[360px]">
                          <p
                            className="font-literata text-sm text-on-surface-variant line-clamp-2"
                            title={r.message}
                          >
                            {r.message}
                          </p>
                        </td>
                        <td className="px-5 py-4 whitespace-nowrap">
                          <div className="flex items-center gap-3">
                            <span
                              className={cn(
                                "inline-flex items-center gap-1.5 text-[11px] font-literata capitalize",
                                r.status === "resolved"
                                  ? "text-emerald-700"
                                  : "text-secondary",
                              )}
                            >
                              <span
                                className={cn(
                                  "w-1.5 h-1.5 rounded-full",
                                  r.status === "resolved"
                                    ? "bg-emerald-600"
                                    : "bg-secondary-container",
                                )}
                              />
                              {r.status}
                            </span>
                            <button
                              onClick={() => toggleStatus(r)}
                              disabled={updatingId === r.id}
                              className="inline-flex items-center gap-1 px-3 py-1 rounded-full border border-outline-variant/30 text-[10px] font-semibold font-literata text-primary hover:bg-surface-container transition-colors disabled:opacity-40 cursor-pointer"
                            >
                              {r.status === "resolved" ? (
                                <>
                                  <RotateCcw className="w-3 h-3" />
                                  Reopen
                                </>
                              ) : (
                                <>
                                  <Check className="w-3 h-3" />
                                  Resolve
                                </>
                              )}
                            </button>
                          </div>
                        </td>
                        <td className="px-5 py-4 font-literata text-sm text-on-surface-variant whitespace-nowrap">
                          {formatDate(r.created_at)}
                        </td>
                      </tr>
                    ))}
                {!loading && rows.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-5 py-12 text-center font-literata text-sm text-on-surface-variant/60 italic"
                    >
                      No feedback matches these filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {pagination && pagination.pages > 1 && (
            <div className="flex items-center justify-between px-5 py-4 border-t border-outline-variant/15">
              <span className="font-literata text-xs text-on-surface-variant">
                Page {pagination.page} of {pagination.pages}
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="p-2 rounded-full border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  disabled={page >= pagination.pages}
                  onClick={() => setPage((p) => p + 1)}
                  className="p-2 rounded-full border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                  aria-label="Next page"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
