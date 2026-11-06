"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { authedFetch } from "@/lib/api";
import { 
  Eye, 
  MessageSquare, 
  Clock, 
  RotateCw, 
  Sparkles, 
  Search,
  ChevronLeft,
  ChevronRight,
  AlertTriangle
} from "lucide-react";

interface VideoItem {
  id: string;
  platform: string;
  external_id: string;
  title: string;
  description: string;
  thumbnail_url: string;
  published_at: string;
  view_count: number;
  like_count: number;
  comment_count: number;
  sync_status: string;
  analysis_status: string | null;
  last_synced_at: string | null;
}

export default function VideosPage() {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [pagination, setPagination] = useState({ page: 1, limit: 6, total: 0, pages: 1 });
  const [loading, setLoading] = useState(true);
  
  // Filters & State
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusTab, setStatusTab] = useState<"all" | "analyzed" | "pending">("all");
  const [platformTab, setPlatformTab] = useState<"all" | "youtube" | "tiktok">("all");
  const [sortBy, setSortBy] = useState("published_at");
  const [currentPage, setCurrentPage] = useState(1);
  
  // Sync Actions State
  const [syncing, setSyncing] = useState(false);
  const [syncCount, setSyncCount] = useState<number | null>(null);
  const [analyzingVideoId, setAnalyzingVideoId] = useState<string | null>(null);
  const [syncResult, setSyncResult] = useState<{ success: boolean; message: string } | null>(null);

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
      setCurrentPage(1);
    }, 400);
    return () => clearTimeout(timer);
  }, [search]);

  const fetchVideos = useCallback(async () => {
    setTimeout(() => setLoading(true), 0);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      let url = `${apiUrl}/api/v1/videos?page=${currentPage}&limit=6&sort=${sortBy}`;
      if (debouncedSearch) {
        url += `&search=${encodeURIComponent(debouncedSearch)}`;
      }
      if (statusTab !== "all") {
        url += `&status=${statusTab}`;
      }
      if (platformTab !== "all") {
        url += `&platform=${platformTab}`;
      }

      const res = await authedFetch(url);
      if (res.ok) {
        const payload = await res.json();
        setVideos(payload.data || []);
        setPagination(payload.pagination || { page: 1, limit: 6, total: 0, pages: 1 });
      }
    } catch (e) {
      console.error("Failed to load videos from backend", e);
    } finally {
      setTimeout(() => setLoading(false), 0);
    }
  }, [currentPage, statusTab, platformTab, sortBy, debouncedSearch]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchVideos();
    }, 0);
    return () => clearTimeout(timer);
  }, [fetchVideos]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncCount(null);
    setSyncResult(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const providers = ["youtube", "tiktok"] as const;
      let totalImported = 0;
      let anySucceeded = false;

      for (const provider of providers) {
        try {
          const res = await authedFetch(`${apiUrl}/api/v1/${provider}/sync?limit=24`, {
            method: "POST"
          });
          if (res.ok) {
            const data = await res.json();
            totalImported += data.videos_imported ?? 0;
            anySucceeded = true;
          }
        } catch (e) {
          // Provider not connected or temporarily unavailable; try the next one.
          console.error(`Failed to sync ${provider}`, e);
        }
      }

      if (anySucceeded) {
        setSyncCount(totalImported);
        fetchVideos();
      } else {
        setSyncResult({
          success: false,
          message: "No connected channel to sync. Connect YouTube or TikTok in Settings."
        });
      }
    } finally {
      setSyncing(false);
    }
  };

  const handleAnalyze = async (videoId: string) => {
    setAnalyzingVideoId(videoId);
    setSyncResult(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      const res = await authedFetch(`${apiUrl}/api/v1/videos/${videoId}/comments/sync`, {
        method: "POST"
      });
      
      const payload = await res.json();
      
      if (res.ok && payload.success) {
        const syncedCount = payload.data?.synced_count ?? 0;
        const newStatus = payload.data?.sync_status ?? "synced";
        
        setVideos(prev => 
          prev.map(v => v.id === videoId ? { ...v, sync_status: newStatus, last_synced_at: new Date().toISOString() } : v)
        );
        setSyncResult({
          success: true,
          message: `Successfully synced comments! ${syncedCount} new comments added.`
        });
      } else {
        const errMsg = payload.detail?.message || "Failed to synchronize comments.";
        const errCode = payload.detail?.code;
        
        const newStatus = errCode === "COMMENTS_DISABLED" || errMsg.includes("disabled") ? "disabled" : "pending";
        if (newStatus === "disabled") {
          setVideos(prev => 
            prev.map(v => v.id === videoId ? { ...v, sync_status: "disabled" } : v)
          );
        }
        
        setSyncResult({
          success: false,
          message: `Sync failed: ${errMsg}`
        });
      }
    } catch (e) {
      console.error(e);
      setSyncResult({
        success: false,
        message: "A network error occurred while connecting to the sync service."
      });
    } finally {
      setAnalyzingVideoId(null);
    }
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
    if (num >= 1000) return (num / 1000).toFixed(1) + "k";
    return num.toString();
  };

  const getRelativeTime = (dateString: string) => {
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      
      if (diffDays > 30) {
        const m = Math.floor(diffDays / 30);
        return m === 1 ? "1 month ago" : `${m} months ago`;
      }
      if (diffDays > 0) {
        if (diffDays === 1) return "1 day ago";
        return `${diffDays} days ago`;
      }
      
      const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
      if (diffHrs > 0) return diffHrs === 1 ? "1 hour ago" : `${diffHrs} hours ago`;
      
      return "just now";
     } catch {
      return dateString;
    }
  };

  return (
    <div className="flex flex-col gap-8 text-on-surface">
      {/* Search Syncer Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex flex-col">
          <h1 className="font-playfair text-3xl font-bold text-primary">Your Videos</h1>
          <p className="text-on-surface-variant font-literata text-sm mt-1 max-w-xl leading-relaxed">
            Manage your content library and harness AI-driven audience insights for every upload.
          </p>
        </div>

        <div>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="w-full sm:w-auto px-5 py-2.5 rounded-full bg-primary hover:bg-primary-container text-on-primary text-xs font-semibold font-literata transition-all duration-150 flex items-center justify-center gap-2 shadow-sm disabled:opacity-50 cursor-pointer"
          >
            <RotateCw className={`w-3.5 h-3.5 ${syncing ? "animate-spin" : ""}`} />
            <span>{syncing ? "Syncing Uploads..." : "Sync Videos"}</span>
          </button>
        </div>
      </div>

      {/* Sync Status Overlay / Banner */}
      <AnimatePresence>
        {syncCount !== null && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="p-4 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-2xl flex items-center justify-between font-literata text-xs shadow-sm"
          >
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded-full bg-emerald-200 text-emerald-800 flex items-center justify-center font-bold">✓</div>
              <span>YouTube sync successful! Imported/updated <strong>{syncCount}</strong> videos from your channel.</span>
            </div>
            <button 
              onClick={() => setSyncCount(null)}
              className="text-emerald-600 hover:text-emerald-800 font-bold p-1 cursor-pointer"
            >
              Dismiss
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Comments Sync Status Banner */}
      <AnimatePresence>
        {syncResult !== null && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={cn(
              "p-4 border rounded-2xl flex items-center justify-between font-literata text-xs shadow-sm",
              syncResult.success 
                ? "bg-emerald-50 border-emerald-200 text-emerald-800" 
                : "bg-amber-50 border-amber-200 text-amber-800"
            )}
          >
            <div className="flex items-center gap-2">
              <div className={cn(
                "w-5 h-5 rounded-full flex items-center justify-center font-bold",
                syncResult.success ? "bg-emerald-200 text-emerald-800" : "bg-amber-200 text-amber-800"
              )}>
                {syncResult.success ? "✓" : "!"}
              </div>
              <span>{syncResult.message}</span>
            </div>
            <button 
              onClick={() => setSyncResult(null)}
              className={cn(
                "font-bold p-1 cursor-pointer",
                syncResult.success ? "text-emerald-600 hover:text-emerald-800" : "text-amber-600 hover:text-amber-800"
              )}
            >
              Dismiss
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Filters Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-outline-variant/20 pb-4">
        {/* Tab Pills */}
        <div className="flex flex-wrap items-center gap-4">
        <div className="flex gap-2">
          {([
            { id: "all", label: "All Videos" },
            { id: "analyzed", label: "Analyzed" },
            { id: "pending", label: "Pending" }
          ] as const).map((tab) => {
            const isActive = statusTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setStatusTab(tab.id);
                  setCurrentPage(1);
                }}
                className={cn(
                  "px-4 py-1.5 rounded-full text-xs font-semibold font-literata transition-all cursor-pointer",
                  isActive
                    ? "bg-primary text-on-primary"
                    : "border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container hover:text-primary"
                )}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Platform Filter Pills */}
        <div className="flex gap-2 sm:border-l sm:border-outline-variant/20 sm:pl-4">
          {([
            { id: "all", label: "All Platforms" },
            { id: "youtube", label: "YouTube" },
            { id: "tiktok", label: "TikTok" }
          ] as const).map((tab) => {
            const isActive = platformTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setPlatformTab(tab.id);
                  setCurrentPage(1);
                }}
                className={cn(
                  "px-4 py-1.5 rounded-full text-xs font-semibold font-literata transition-all cursor-pointer border",
                  isActive
                    ? "bg-secondary-container text-primary border-transparent"
                    : "border-outline-variant/30 text-on-surface-variant hover:bg-surface-container hover:text-primary"
                )}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
        </div>

        {/* Sorting Dropdown & Search */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          {/* Dynamic Search Box for Video Library */}
          <div className="relative flex-1 sm:max-w-xs w-full sm:hidden">
            <Search className="w-4 h-4 text-on-surface-variant/60 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search library..."
              className="w-full bg-surface-container-low border border-outline-variant/20 rounded-full py-1.5 pl-9 pr-4 font-literata text-xs focus:outline-none focus:border-primary/40 focus:bg-white transition-colors"
            />
          </div>

          <div className="flex items-center gap-2 text-xs font-literata text-on-surface-variant ml-auto sm:ml-0">
            <span>Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-transparent border-0 font-semibold text-primary focus:ring-0 py-1 pl-1 cursor-pointer focus:outline-none"
            >
              <option value="published_at">Latest Upload</option>
              <option value="views">Most Views</option>
              <option value="comments">Most Comments</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Grid content list */}
      {loading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card-base animate-pulse border border-outline-variant/10 rounded-2xl overflow-hidden h-[360px] flex flex-col justify-between p-4">
              <div className="w-full h-40 bg-surface-container rounded-xl" />
              <div className="h-4 bg-surface-container rounded w-3/4 mt-4" />
              <div className="h-3 bg-surface-container rounded w-1/2 mt-2" />
              <div className="h-10 bg-surface-container rounded-xl w-full mt-6" />
            </div>
          ))}
        </div>
      ) : videos.length === 0 ? (
        <div className="py-16 text-center flex flex-col items-center gap-4 border border-dashed border-outline-variant/30 rounded-3xl bg-white/40">
          <div className="w-16 h-16 rounded-full bg-surface-container flex items-center justify-center">
            <Search className="w-6 h-6 text-on-surface-variant/40" />
          </div>
          <div className="flex flex-col max-w-sm">
            <h3 className="font-playfair text-lg font-bold text-primary">No videos found</h3>
            <p className="text-xs text-on-surface-variant font-literata mt-1">
              {debouncedSearch 
                ? "No uploads match your search criteria. Try modifying keywords."
                : "No uploads imported yet. Sync your YouTube account to load video files."}
            </p>
          </div>
          {!debouncedSearch && (
            <button
              onClick={handleSync}
              className="px-5 py-2 border border-primary text-primary font-literata text-xs font-semibold rounded-full hover:bg-surface-container cursor-pointer transition-colors"
            >
              Sync Channels Now
            </button>
          )}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {videos.map((video) => {
            const isAnalyzed = video.analysis_status === "completed";
            const analysisInProgress =
              video.analysis_status === "pending" ||
              video.analysis_status === "running";
            const commentsSynced = video.sync_status === "synced";
            const isAnalyzing = analyzingVideoId === video.id;

            return (
              <div 
                key={video.id}
                className="bg-white border border-outline-variant/10 rounded-2xl overflow-hidden shadow-sm flex flex-col justify-between group hover:shadow-md transition-shadow h-[380px]"
              >
                {/* Thumbnail and badges */}
                <div className="relative w-full h-44 overflow-hidden bg-surface-container-high flex-shrink-0">
                  {video.thumbnail_url ? (
                    <img
                      src={video.thumbnail_url}
                      alt={video.title}
                      className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-103"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-on-surface-variant/20 font-literata text-xs">
                      No Thumbnail Available
                    </div>
                  )}

                  {/* Top-Right Platform Badge */}
                  <div className="absolute top-3 right-3">
                    <span className={cn(
                      "text-[10px] font-bold font-literata px-2.5 py-1 rounded-full shadow-sm border",
                      video.platform === "tiktok"
                        ? "bg-white/95 text-primary border-outline-variant/30"
                        : "bg-white/95 text-red-700 border-red-200"
                    )}>
                      {video.platform === "tiktok" ? "TikTok" : "YouTube"}
                    </span>
                  </div>

                  {/* Top-Left Analysis Status Badge */}
                  <div className="absolute top-3 left-3">
                    {isAnalyzed ? (
                      <span className="ai-badge bg-[#ffe088] text-[#241a00] border-[#e9c349] shadow-sm flex items-center gap-1">
                        <Sparkles className="w-2.5 h-2.5 text-secondary" />
                        <span>Analyzed</span>
                      </span>
                    ) : analysisInProgress ? (
                      <span className="bg-sky-50 text-sky-700 border border-sky-200 text-[10px] font-semibold font-literata px-2.5 py-1 rounded-full shadow-sm flex items-center gap-1">
                        <RotateCw className="w-2.5 h-2.5 text-sky-500 animate-spin" />
                        <span>Analyzing</span>
                      </span>
                    ) : video.sync_status === "disabled" ? (
                      <span className="bg-amber-50 text-amber-700 border border-amber-200 text-[10px] font-semibold font-literata px-2.5 py-1 rounded-full shadow-sm flex items-center gap-1">
                        <AlertTriangle className="w-2.5 h-2.5 text-amber-500" />
                        <span>Disabled</span>
                      </span>
                    ) : commentsSynced ? (
                      <span className="bg-white/95 text-primary border border-outline-variant/30 text-[10px] font-semibold font-literata px-2.5 py-1 rounded-full shadow-sm flex items-center gap-1">
                        <Sparkles className="w-2.5 h-2.5 text-secondary" />
                        <span>Ready to Analyze</span>
                      </span>
                    ) : (
                      <span className="bg-white/95 text-primary border border-outline-variant/30 text-[10px] font-semibold font-literata px-2.5 py-1 rounded-full shadow-sm flex items-center gap-1">
                        <Clock className="w-2.5 h-2.5 text-on-surface-variant" />
                        <span>Pending</span>
                      </span>
                    )}
                  </div>
                </div>

                {/* Card Title & Content */}
                <div className="p-4 flex-1 flex flex-col justify-between">
                  <div className="flex flex-col gap-1.5">
                    <h3 className="font-playfair text-base font-bold text-primary line-clamp-2 group-hover:text-primary-container leading-snug">
                      {video.title}
                    </h3>
                  </div>

                  <div className="flex flex-col gap-4 mt-auto">
                    {/* Stats metrics */}
                    <div className="flex items-center gap-4 text-xs text-on-surface-variant font-literata border-t border-outline-variant/10 pt-3">
                      <div className="flex items-center gap-1">
                        <Eye className="w-3.5 h-3.5 text-on-surface-variant/70" />
                        <span>{formatNumber(video.view_count)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <MessageSquare className="w-3.5 h-3.5 text-on-surface-variant/70" />
                        <span>{formatNumber(video.comment_count)}</span>
                      </div>
                      <div className="flex items-center gap-1 ml-auto text-[10px] text-on-surface-variant/80">
                        <Clock className="w-3 h-3 text-on-surface-variant/60" />
                        <span>{getRelativeTime(video.published_at)}</span>
                      </div>
                    </div>

                    {/* Action buttons */}
                    {isAnalyzed ? (
                      <Link
                        href={`/dashboard/videos/${video.id}`}
                        className="w-full bg-surface-container hover:bg-surface-container-high text-primary font-literata text-xs font-semibold py-2.5 rounded-xl border border-primary/5 transition-colors cursor-pointer text-center block"
                      >
                        View Insights
                      </Link>
                    ) : analysisInProgress ? (
                      <Link
                        href={`/dashboard/videos/${video.id}`}
                        className="w-full bg-surface-container hover:bg-surface-container-high text-primary font-literata text-xs font-semibold py-2.5 rounded-xl border border-primary/5 transition-colors cursor-pointer text-center block"
                      >
                        View Progress
                      </Link>
                    ) : video.sync_status === "disabled" ? (
                      <button 
                        disabled 
                        className="w-full bg-surface-container-low text-on-surface-variant/40 font-literata text-xs font-semibold py-2.5 rounded-xl border border-outline-variant/10 text-center cursor-not-allowed"
                      >
                        Sync Unavailable
                      </button>
                    ) : commentsSynced ? (
                      <Link
                        href={`/dashboard/videos/${video.id}`}
                        className="w-full bg-primary hover:bg-primary-container text-on-primary font-literata text-xs font-semibold py-2.5 rounded-xl transition-all flex items-center justify-center gap-1.5 shadow-sm hover:shadow cursor-pointer"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-secondary-container" />
                        <span>Analyze Comments</span>
                      </Link>
                    ) : (
                      <button
                        onClick={() => handleAnalyze(video.id)}
                        disabled={isAnalyzing}
                        className="w-full bg-primary hover:bg-primary-container text-on-primary font-literata text-xs font-semibold py-2.5 rounded-xl transition-all flex items-center justify-center gap-1.5 shadow-sm hover:shadow cursor-pointer disabled:opacity-50"
                      >
                        {isAnalyzing ? (
                          <>
                            <RotateCw className="w-3.5 h-3.5 animate-spin" />
                            <span>Syncing Comments...</span>
                          </>
                        ) : (
                          <>
                            <RotateCw className="w-3.5 h-3.5 text-secondary-container" />
                            <span>Sync Comments</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Row */}
      {pagination.pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <button
            onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
            disabled={currentPage === 1 || loading}
            className="p-2 border border-outline-variant/30 rounded-xl hover:bg-surface-container disabled:opacity-30 cursor-pointer"
            aria-label="Previous page"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          
          {[...Array(pagination.pages)].map((_, i) => {
            const pageNum = i + 1;
            const isActive = currentPage === pageNum;
            return (
              <button
                key={pageNum}
                onClick={() => setCurrentPage(pageNum)}
                disabled={loading}
                className={cn(
                  "w-8 h-8 rounded-full font-literata text-xs font-semibold transition-all cursor-pointer flex items-center justify-center",
                  isActive
                    ? "bg-[#0b3d2e] text-white shadow-sm"
                    : "hover:bg-surface-container text-on-surface-variant"
                )}
              >
                {pageNum}
              </button>
            );
          })}

          <button
            onClick={() => setCurrentPage(prev => Math.min(prev + 1, pagination.pages))}
            disabled={currentPage === pagination.pages || loading}
            className="p-2 border border-outline-variant/30 rounded-xl hover:bg-surface-container disabled:opacity-30 cursor-pointer"
            aria-label="Next page"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
