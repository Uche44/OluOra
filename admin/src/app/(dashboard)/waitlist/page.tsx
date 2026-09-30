"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Search, ChevronLeft, ChevronRight, Download } from "lucide-react";
import { getJson } from "@/lib/http";
import { formatDate } from "@/lib/utils";

interface WaitlistRow {
  id: string;
  email: string;
  source: string;
  created_at: string;
  ip_address: string | null;
}

interface PaginatedWaitlist {
  data: WaitlistRow[];
  pagination: { page: number; limit: number; total: number; pages: number };
}

export default function WaitlistPage() {
  const [rows, setRows] = useState<WaitlistRow[]>([]);
  const [pagination, setPagination] = useState<PaginatedWaitlist["pagination"] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    setPage(1);
  }, [debounced]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ page: String(page), limit: "20" });
      if (debounced) params.set("search", debounced);
      const data = await getJson<PaginatedWaitlist>(`/admin/waitlist?${params.toString()}`);
      setRows(data.data);
      setPagination(data.pagination);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load waitlist.");
    } finally {
      setLoading(false);
    }
  }, [page, debounced]);

  useEffect(() => {
    load();
  }, [load]);

  const exportCsv = () => {
    const header = "email,source,created_at,ip_address";
    const body = rows
      .map((r) =>
        [r.email, r.source, r.created_at, r.ip_address ?? ""]
          .map((v) => `"${String(v).replace(/"/g, '""')}"`)
          .join(","),
      )
      .join("\n");
    const blob = new Blob([`${header}\n${body}`], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `oluora-waitlist-page-${page}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-6 text-on-surface"
    >
      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-col">
          <h1 className="font-playfair text-3xl font-bold text-primary">Waitlist</h1>
          <p className="text-on-surface-variant font-literata text-sm mt-1">
            {pagination ? `${pagination.total} signups` : "Landing page signups."}
          </p>
        </div>
        <button
          onClick={exportCsv}
          disabled={rows.length === 0}
          className="flex items-center gap-2 px-4 py-2 rounded-full border border-outline-variant/30 text-xs font-semibold font-literata text-primary hover:bg-surface-container disabled:opacity-40 transition"
        >
          <Download className="w-3.5 h-3.5" />
          Export page (CSV)
        </button>
      </div>

      <div className="relative max-w-md">
        <Search className="w-4 h-4 text-on-surface-variant/60 absolute left-3 top-1/2 -translate-y-1/2" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by email..."
          className="w-full bg-surface-container-low border border-outline-variant/20 rounded-full py-2 pl-10 pr-4 font-literata text-sm focus:outline-none focus:border-primary/40 focus:bg-surface-container-lowest transition-colors"
        />
      </div>

      {error ? (
        <div className="p-6 bg-red-50 border border-red-200 text-red-900 rounded-3xl flex flex-col gap-4 font-literata text-sm">
          <div className="flex items-center gap-2 text-red-700 font-bold">
            <AlertTriangle className="w-5 h-5" />
            <span>Error loading waitlist</span>
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
                  <th className="px-5 py-3 font-medium">Email</th>
                  <th className="px-5 py-3 font-medium">Source</th>
                  <th className="px-5 py-3 font-medium">Joined</th>
                </tr>
              </thead>
              <tbody>
                {loading
                  ? Array.from({ length: 6 }).map((_, i) => (
                      <tr key={i} className="border-b border-outline-variant/10">
                        <td colSpan={3} className="px-5 py-4">
                          <div className="h-4 bg-surface-container rounded animate-pulse" />
                        </td>
                      </tr>
                    ))
                  : rows.map((r) => (
                      <tr
                        key={r.id}
                        className="border-b border-outline-variant/10 last:border-0 hover:bg-surface-container/30 transition-colors"
                      >
                        <td className="px-5 py-4 font-literata text-sm text-primary">{r.email}</td>
                        <td className="px-5 py-4">
                          <span className="text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-full border border-outline-variant/30 text-on-surface-variant">
                            {r.source}
                          </span>
                        </td>
                        <td className="px-5 py-4 font-literata text-sm text-on-surface-variant">
                          {formatDate(r.created_at)}
                        </td>
                      </tr>
                    ))}
                {!loading && rows.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-5 py-12 text-center font-literata text-sm text-on-surface-variant/60 italic">
                      No waitlist entries match.
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
