"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Search, ChevronLeft, ChevronRight } from "lucide-react";
import { getJson } from "@/lib/http";
import { cn, formatDate } from "@/lib/utils";

interface AdminUserRow {
  id: string;
  email: string;
  full_name: string | null;
  plan: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  connections: number;
  videos: number;
}

interface PaginatedUsers {
  data: AdminUserRow[];
  pagination: { page: number; limit: number; total: number; pages: number };
}

const PLAN_OPTIONS = ["", "free", "pro"];
const STATUS_OPTIONS = [
  { label: "All", value: "" },
  { label: "Active", value: "true" },
  { label: "Suspended", value: "false" },
];

export default function UsersPage() {
  const [rows, setRows] = useState<AdminUserRow[]>([]);
  const [pagination, setPagination] = useState<PaginatedUsers["pagination"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [plan, setPlan] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debounced, plan, status]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(page), limit: "20" });
      if (debounced) params.set("search", debounced);
      if (plan) params.set("plan", plan);
      if (status) params.set("is_active", status);
      const data = await getJson<PaginatedUsers>(`/admin/users?${params.toString()}`);
      setRows(data.data);
      setPagination(data.pagination);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  }, [page, debounced, plan, status]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-6 text-on-surface"
    >
      <div className="flex flex-col">
        <h1 className="font-playfair text-3xl font-bold text-primary">Users</h1>
        <p className="text-on-surface-variant font-literata text-sm mt-1">
          {pagination ? `${pagination.total} accounts` : "All registered creators."}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 text-on-surface-variant/60 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by email or name..."
            className="w-full bg-surface-container-low border border-outline-variant/20 rounded-full py-2 pl-10 pr-4 font-literata text-sm focus:outline-none focus:border-primary/40 focus:bg-surface-container-lowest transition-colors"
          />
        </div>

        <div className="flex items-center gap-1">
          {PLAN_OPTIONS.map((p) => (
            <button
              key={p || "all"}
              onClick={() => setPlan(p)}
              className={cn(
                "px-4 py-2 rounded-full text-xs font-literata font-semibold transition-colors capitalize",
                plan === p
                  ? "bg-primary text-on-primary"
                  : "border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container",
              )}
            >
              {p || "All plans"}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1">
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s.label}
              onClick={() => setStatus(s.value)}
              className={cn(
                "px-4 py-2 rounded-full text-xs font-literata font-semibold transition-colors",
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
            <span>Error loading users</span>
          </div>
          <p>{error}</p>
          <button
            onClick={load}
            className="px-5 py-2 rounded-full bg-red-700 text-white font-semibold self-start hover:bg-red-800 transition"
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
                  <th className="px-5 py-3 font-medium">Plan</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Connections</th>
                  <th className="px-5 py-3 font-medium">Videos</th>
                  <th className="px-5 py-3 font-medium">Joined</th>
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
                  : rows.map((u) => (
                      <tr
                        key={u.id}
                        className="border-b border-outline-variant/10 last:border-0 hover:bg-surface-container/30 transition-colors"
                      >
                        <td className="px-5 py-4">
                          <div className="flex flex-col">
                            <span className="font-literata text-sm text-primary">
                              {u.full_name || "—"}
                              {u.is_admin && (
                                <span className="ml-2 ai-badge !text-[9px]">admin</span>
                              )}
                            </span>
                            <span className="text-[11px] text-on-surface-variant">{u.email}</span>
                          </div>
                        </td>
                        <td className="px-5 py-4">
                          <span
                            className={cn(
                              "text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-full border capitalize",
                              u.plan === "pro"
                                ? "border-secondary/30 text-secondary bg-secondary/5"
                                : "border-outline-variant/30 text-on-surface-variant",
                            )}
                          >
                            {u.plan}
                          </span>
                        </td>
                        <td className="px-5 py-4">
                          <span
                            className={cn(
                              "inline-flex items-center gap-1.5 text-[11px] font-literata",
                              u.is_active ? "text-emerald-700" : "text-error",
                            )}
                          >
                            <span
                              className={cn(
                                "w-1.5 h-1.5 rounded-full",
                                u.is_active ? "bg-emerald-600" : "bg-error",
                              )}
                            />
                            {u.is_active ? "Active" : "Suspended"}
                          </span>
                        </td>
                        <td className="px-5 py-4 font-literata text-sm text-on-surface-variant">
                          {u.connections}
                        </td>
                        <td className="px-5 py-4 font-literata text-sm text-on-surface-variant">
                          {u.videos}
                        </td>
                        <td className="px-5 py-4 font-literata text-sm text-on-surface-variant">
                          {formatDate(u.created_at)}
                        </td>
                      </tr>
                    ))}
                {!loading && rows.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-5 py-12 text-center font-literata text-sm text-on-surface-variant/60 italic">
                      No users match these filters.
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
                  className="p-2 rounded-full border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container disabled:opacity-40 disabled:cursor-not-allowed transition"
                  aria-label="Previous page"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  disabled={page >= pagination.pages}
                  onClick={() => setPage((p) => p + 1)}
                  className="p-2 rounded-full border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container disabled:opacity-40 disabled:cursor-not-allowed transition"
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
