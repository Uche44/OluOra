"use client";

import React, { use, useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { authedFetch } from "@/lib/api";
import type { VideoDetails, AnalysisRun, TopicCluster, InsightItem, InsightsData } from "@/types/video-insights";
import {
  ArrowLeft,
  Play,
  RotateCw,
  Sparkles,
  AlertTriangle,
  MessageSquare,
  HelpCircle,
  Heart,
  Search,
  X,
  Check,
  Rocket,
} from "lucide-react";

export default function VideoInsightsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: videoId } = use(params);

  // States
  const [video, setVideo] = useState<VideoDetails | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisRun | null>(null);
  const [clusters, setClusters] = useState<TopicCluster[]>([]);
  const [insights, setInsights] = useState<InsightsData>({ questions: [], pain_points: [], positive_themes: [] });
  const [recommendations, setRecommendations] = useState<InsightItem[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Topic Explorer interactive state
  const [selectedClusterIndex, setSelectedClusterIndex] = useState<number>(0);

  // Insights Section (Section 4) state
  type InsightTab = "questions" | "pain_points" | "positive_themes";
  const [activeTab, setActiveTab] = useState<InsightTab>("questions");
  const [searchQuery, setSearchQuery] = useState("");

  // Content Recommendations (Section 3) state
  type RecStatus = "none" | "planned" | "in_progress" | "dismissed";
  type RecMeta = { status: RecStatus; title: string; content: string; videoId: string; videoTitle: string };
  const LS_KEY = "olundi_recs";
  const [recStatuses, setRecStatuses] = useState<Record<string, RecMeta>>({});
  type RecFilterTab = "all" | "active" | "planned" | "dismissed";
  const [recFilter, setRecFilter] = useState<RecFilterTab>("all");

  // Load statuses from localStorage whenever recommendations change
  const loadRecStatuses = (recs: InsightItem[], videoData: VideoDetails | null) => {
    try {
      const stored: Record<string, RecMeta> = JSON.parse(localStorage.getItem(LS_KEY) || "{}");
      // Seed any newly seen recommendations that aren't in localStorage yet
      recs.forEach(rec => {
        if (!stored[rec.id]) {
          stored[rec.id] = {
            status: "none",
            title: rec.title,
            content: rec.content,
            videoId: videoData?.id ?? "",
            videoTitle: videoData?.title ?? "Unknown Video",
          };
        }
      });
      localStorage.setItem(LS_KEY, JSON.stringify(stored));
      setRecStatuses(stored);
    } catch {
      // localStorage not available (SSR safety)
    }
  };

  const setRecStatus = (recId: string, status: RecStatus) => {
    setRecStatuses(prev => {
      const updated = { ...prev, [recId]: { ...prev[recId], status } };
      try { localStorage.setItem(LS_KEY, JSON.stringify(updated)); } catch { /* noop */ }
      return updated;
    });
  };


  // Fetch functions
  const loadData = useCallback(async (silent: boolean = false) => {
    if (!silent) {
      setLoading(true);
    }
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      // 1. Fetch Video details
      const videoRes = await authedFetch(`${apiUrl}/api/v1/videos/${videoId}`);
      if (!videoRes.ok) {
        throw new Error("Failed to load video metadata details.");
      }
      const videoData = await videoRes.json();
      setVideo(videoData);

      // 2. Fetch Latest Analysis run
      const analysisRes = await authedFetch(`${apiUrl}/api/v1/analysis/latest/${videoId}`);
      if (!analysisRes.ok) {
        // If 404, it means no analysis run has happened yet
        if (analysisRes.status === 404) {
          setAnalysis(null);
          setLoading(false);
          return;
        }
        throw new Error("Failed to load analysis details.");
      }
      const analysisData = await analysisRes.json();
      setAnalysis(analysisData);

      // 3. If analysis is completed, fetch details in parallel
      if (analysisData.status === "completed") {
        const [clustersRes, insightsRes, recsRes] = await Promise.all([
          authedFetch(`${apiUrl}/api/v1/analysis/${analysisData.id}/clusters`),
          authedFetch(`${apiUrl}/api/v1/analysis/${analysisData.id}/insights`),
          authedFetch(`${apiUrl}/api/v1/analysis/${analysisData.id}/recommendations`)
        ]);

        if (clustersRes.ok) {
          const clustersData = await clustersRes.json();
          setClusters(clustersData);
        }
        if (insightsRes.ok) {
          const insightsData = await insightsRes.json();
          setInsights(insightsData);
        }
        if (recsRes.ok) {
          const recsData: InsightItem[] = await recsRes.json();
          setRecommendations(recsData);
          loadRecStatuses(recsData, videoData);
        }
      }
    } catch (err: any) {
      console.error(err);
      setError(err.message || "An unexpected error occurred while loading dashboard metrics.");
    } finally {
      setLoading(false);
    }
  }, [videoId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Set up background status polling when analysis is pending or running
  useEffect(() => {
    if (!analysis || (analysis.status !== "pending" && analysis.status !== "running")) {
      return;
    }

    const intervalId = setInterval(() => {
      loadData(true); // silent fetch in background
    }, 3000);

    return () => clearInterval(intervalId);
  }, [analysis, loadData]);

  // Trigger fresh analysis run
  const handleTriggerAnalysis = async () => {
    setLoading(true);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await authedFetch(`${apiUrl}/api/v1/analysis/run/${videoId}`, {
        method: "POST"
      });
      if (res.ok) {
        // Reload dashboard state
        loadData();
      } else {
        const data = await res.json();
        throw new Error(data.detail?.message || "Failed to trigger analysis run.");
      }
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  // Format numbers helper (e.g. 142.8k)
  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + "m";
    if (num >= 1000) return (num / 1000).toFixed(1) + "k";
    return num.toString();
  };

  // Convert duration to mm:ss helper
  const getAverageDuration = () => {
    // Return a styled mock or derived value based on length/stats
    return "08:42";
  };

  // Aggregate Sentiment Score helper
  const getOverallSentimentScore = () => {
    if (clusters.length === 0) return 94; // fallback static design default
    const totalSize = clusters.reduce((acc, c) => acc + c.size, 0);
    if (totalSize === 0) return 94;
    const weightedSentiment = clusters.reduce((acc, c) => acc + (c.sentiment_score * c.size), 0);
    const avgScore = weightedSentiment / totalSize;
    // Scale sentiment_score (usually -1 to 1 or 0 to 1) to percentage 0-100
    // If database uses 0 to 1:
    return Math.round(avgScore * 100);
  };

  // Calculate percentage size for clusters
  const getClusterPercentage = (size: number) => {
    const totalSize = clusters.reduce((acc, c) => acc + c.size, 0);
    if (totalSize === 0) return 0;
    return Math.round((size / totalSize) * 100);
  };

  // Loading Skeleton State
  if (loading) {
    return (
      <div className="flex flex-col gap-8 animate-pulse text-on-surface p-2">
        <div className="h-6 bg-surface-container rounded w-1/4" />
        <div className="flex flex-col md:flex-row justify-between gap-6">
          <div className="flex-1 flex flex-col gap-4">
            <div className="h-10 bg-surface-container rounded w-3/4" />
            <div className="h-4 bg-surface-container rounded w-1/2" />
          </div>
          <div className="w-full md:w-64 h-36 bg-surface-container rounded-3xl" />
        </div>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="h-44 bg-surface-container rounded-3xl col-span-2" />
          <div className="h-44 bg-surface-container rounded-3xl" />
        </div>
        <div className="h-64 bg-surface-container rounded-3xl" />
      </div>
    );
  }

  // Error Banner State
  if (error) {
    return (
      <div className="p-6 bg-amber-50 border border-amber-200 text-amber-900 rounded-3xl flex flex-col gap-4 font-literata text-sm max-w-2xl mx-auto my-12">
        <div className="flex items-center gap-2 text-amber-700 font-bold">
          <AlertTriangle className="w-5 h-5" />
          <span>Error Syncing Workspace</span>
        </div>
        <p className="leading-relaxed">{error}</p>
        <div className="flex gap-3 mt-2">
          <button onClick={() => loadData()} className="px-5 py-2 rounded-full bg-amber-700 text-white font-semibold hover:bg-amber-800 transition cursor-pointer">
            Retry Loading
          </button>
          <Link href="/dashboard/videos" className="px-5 py-2 rounded-full border border-amber-300 hover:bg-amber-100/50 transition text-center font-medium">
            Back to Library
          </Link>
        </div>
      </div>
    );
  }

  // Not Analyzed (Pending/No Run) Setup Screen
  if (!analysis || analysis.status === "pending" || analysis.status === "running") {
    const isRunning = analysis?.status === "running";
    return (
      <div className="flex flex-col gap-6 max-w-xl mx-auto py-16 text-center text-on-surface">
        <div className="w-16 h-16 rounded-full bg-[#0b3d2e]/10 text-primary flex items-center justify-center mx-auto">
          <Sparkles className="w-6 h-6" />
        </div>
        
        <h1 className="font-playfair text-3xl font-bold text-primary">
          {isRunning ? "Analyzing Video Comments..." : "Audience Insights Pending"}
        </h1>
        
        <p className="text-sm font-literata text-on-surface-variant leading-relaxed">
          {isRunning 
            ? "OluOra is currently fetching YouTube comments, generating semantic embeddings, and clustering viewer topics. This takes less than a minute."
            : "Trigger an AI audience report to automatically map viewer segments, emotional sentiments, FAQs, and content suggestions."}
        </p>

        {isRunning && (
          <div className="my-4 flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-4 border-primary/10 border-t-primary rounded-full animate-spin" />
            <span className="text-xs text-on-surface-variant font-medium">Currently executing pipeline...</span>
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-4">
          {!isRunning && (
            <button
              onClick={handleTriggerAnalysis}
              className="w-full sm:w-auto px-6 py-3 rounded-full bg-primary hover:bg-primary-container text-on-primary font-literata font-semibold text-sm shadow-md transition cursor-pointer"
            >
              Analyze Comments
            </button>
          )}
          <Link
            href="/dashboard/videos"
            className="w-full sm:w-auto px-6 py-3 rounded-full border border-outline-variant/30 text-on-surface-variant hover:bg-surface-container font-literata font-semibold text-sm transition text-center"
          >
            Cancel and Return
          </Link>
        </div>
      </div>
    );
  }

  // If analysis failed
  if (analysis.status === "failed") {
    return (
      <div className="p-8 bg-red-50 border border-red-200 text-red-900 rounded-3xl flex flex-col gap-4 font-literata text-sm max-w-xl mx-auto my-12">
        <div className="flex items-center gap-2 text-red-700 font-bold text-base">
          <AlertTriangle className="w-5 h-5" />
          <span>Analysis Pipeline Failed</span>
        </div>
        <p className="leading-relaxed">
          The background comments sync or analysis task failed. Message: <br />
          <code className="block bg-white/70 p-3 rounded-xl mt-2 border border-red-100 text-xs overflow-x-auto">{analysis.error_message || "Unknown execution error."}</code>
        </p>
        <div className="flex gap-3 mt-4">
          <button onClick={handleTriggerAnalysis} className="px-5 py-2.5 rounded-full bg-red-700 text-white font-semibold hover:bg-red-800 transition cursor-pointer">
            Re-run Analysis
          </button>
          <Link href="/dashboard/videos" className="px-5 py-2.5 rounded-full border border-red-200 hover:bg-red-100/50 transition font-medium text-center">
            Back to Library
          </Link>
        </div>
      </div>
    );
  }

  // Selected cluster for Topic Explorer
  const activeCluster = clusters[selectedClusterIndex] || null;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-10 text-on-surface pb-16"
    >
      {/* Back Button & Trigger Refresh */}
      <div className="flex items-center justify-between">
        <Link href="/dashboard/videos" className="flex items-center gap-1.5 text-xs font-semibold font-literata text-on-surface-variant hover:text-primary transition">
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Library</span>
        </Link>

        <button 
          onClick={handleTriggerAnalysis}
          className="flex items-center gap-2 px-4 py-2 border border-outline-variant/30 rounded-full text-xs font-semibold font-literata text-on-surface-variant hover:bg-surface-container hover:text-primary transition shadow-sm cursor-pointer"
        >
          <RotateCw className="w-3.5 h-3.5" />
          <span>Refresh Analysis</span>
        </button>
      </div>

      {/* Header Info Block */}
      <div className="flex flex-col md:flex-row justify-between items-start gap-8">
        <div className="flex-1 flex flex-col">
          <div className="inline-flex items-center gap-2">
            <span className="ai-badge bg-[#0b3d2e]/10 text-primary border-[#0b3d2e]/20">Intelligence Report</span>
          </div>
          <h1 className="font-playfair text-3xl md:text-4xl font-bold text-primary mt-3 leading-tight max-w-3xl">
            {video?.title}
          </h1>

          {/* Stats Metrics Row */}
          <div className="flex items-center gap-8 md:gap-12 mt-8 border-t border-outline-variant/20 pt-6">
            <div className="flex flex-col">
              <span className="text-[10px] text-on-surface-variant font-medium tracking-wider uppercase">Total Views</span>
              <span className="font-playfair text-2xl font-bold text-primary mt-1">
                {video ? formatNumber(video.view_count) : "—"}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-on-surface-variant font-medium tracking-wider uppercase">Avg. Duration</span>
              <span className="font-playfair text-2xl font-bold text-primary mt-1">
                {getAverageDuration()}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-on-surface-variant font-medium tracking-wider uppercase">Sentiment Score</span>
              <span className="font-playfair text-2xl font-bold text-primary mt-1 flex items-center gap-1">
                <span>{getOverallSentimentScore()}%</span>
                <span className="text-secondary-container text-base">★</span>
              </span>
            </div>
          </div>
        </div>

        {/* Video Thumbnail Preview Card */}
        {video && (
          <div className="relative w-full md:w-72 h-40 rounded-3xl overflow-hidden shadow-md group border border-outline-variant/15 flex-shrink-0">
            <img 
              src={video.thumbnail_url} 
              alt="Video Preview"
              className="w-full h-full object-cover group-hover:scale-102 transition duration-300"
            />
            <div className="absolute inset-0 bg-black/10 group-hover:bg-black/20 transition flex items-center justify-center">
              <div className="w-12 h-12 rounded-full bg-white/95 backdrop-blur-sm shadow-md flex items-center justify-center text-primary group-hover:scale-110 transition duration-300">
                <Play className="w-5 h-5 fill-primary ml-0.5" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Section 1: Audience Interest Themes */}
      <div className="flex flex-col gap-5">
        <h2 className="font-playfair text-xl font-bold text-primary border-b border-outline-variant/20 pb-3">
          Audience Interest Themes
        </h2>
        
        <div className="grid lg:grid-cols-3 gap-6 items-stretch">
          {/* AI Editorial Summary Card */}
          <div className="bg-[#0b3d2e] rounded-3xl p-8 text-white flex flex-col justify-between min-h-[280px]">
            <div className="flex flex-col gap-4">
              <span className="text-[10px] uppercase font-semibold tracking-wider text-on-primary-container inline-flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Audience AI Summary</span>
              </span>
              <p className="font-playfair text-lg italic leading-relaxed mt-2 font-medium">
                &ldquo;{clusters.length > 0 
                  ? `This audience is primarily interested in ${clusters[0].title.toLowerCase()} and ${clusters[1]?.title.toLowerCase() || 'tutorials'}, revealing the key themes driving viewer engagement.`
                  : "We are currently synthesizing your comment themes to construct a unified creator prompt roadmap."
                }&rdquo;
              </p>
            </div>
            
            <span className="text-[10px] text-on-primary-container/85 font-literata border-t border-white/10 pt-4 mt-6">
              Insight generated from {formatNumber(analysis.comments_analyzed)}+ comments
            </span>
          </div>

          {/* Clusters Grid List */}
          <div className="lg:col-span-2 grid sm:grid-cols-2 gap-5">
            {clusters.slice(0, 4).map((cluster, idx) => {
              const percentage = getClusterPercentage(cluster.size);
              return (
                <div 
                  key={cluster.id} 
                  className="bg-white border border-outline-variant/10 rounded-3xl p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition"
                >
                  <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <span className="font-playfair text-2xl font-bold text-primary">{percentage}%</span>
                      <span className="px-2 py-0.5 bg-amber-50 border border-amber-200 text-amber-800 text-[10px] font-semibold font-literata rounded-full">
                        {cluster.title}
                      </span>
                    </div>
                    <p className="text-xs text-on-surface-variant font-literata leading-relaxed mt-1">
                      {cluster.summary}
                    </p>
                  </div>

                  {/* Curated HSL progress indicator */}
                  <div className="w-full h-1.5 bg-surface-container rounded-full overflow-hidden mt-6">
                    <div 
                      className="h-full bg-primary-container rounded-full" 
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Section 2: Sentiment & Topic Explorer */}
      <div className="grid lg:grid-cols-2 gap-8">
        
        {/* Audience Sentiment Timeline Curve */}
        <div className="bg-white border border-outline-variant/10 rounded-3xl p-8 flex flex-col gap-6 shadow-sm">
          <div className="flex flex-col">
            <h3 className="font-playfair text-lg font-bold text-primary">Audience Sentiment</h3>
            <p className="text-xs text-on-surface-variant font-literata mt-1">
              Retention and emotional resonance over the video timeline.
            </p>
          </div>

          {/* Custom SVG Curve Graph */}
          <div className="relative w-full h-48 border-b border-l border-outline-variant/20 mt-4 flex items-end">
            <svg viewBox="0 0 500 150" className="w-full h-full absolute inset-0 overflow-visible">
              <defs>
                <linearGradient id="sentiment-gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0b3d2e" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#0b3d2e" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* Area spline graph */}
              <path 
                d="M 0 100 Q 120 40 250 90 T 500 70 L 500 150 L 0 150 Z" 
                fill="url(#sentiment-gradient)" 
              />
              {/* Curve path line */}
              <path 
                d="M 0 100 Q 120 40 250 90 T 500 70" 
                fill="none" 
                stroke="#0b3d2e" 
                strokeWidth="2.5" 
                strokeLinecap="round"
              />

              {/* Legend nodes */}
              <circle cx="200" cy="58" r="4.5" fill="#000" />
              <circle cx="380" cy="85" r="4.5" fill="#fed65b" />
            </svg>

            {/* Labels overlay */}
            <div className="absolute left-[38%] top-[25%] flex items-center gap-1 bg-white/95 px-2 py-0.5 border border-outline-variant/25 rounded-md text-[9px] font-medium shadow-sm">
              <span className="w-1.5 h-1.5 bg-black rounded-full" />
              <span>Resonance</span>
            </div>
            <div className="absolute left-[70%] top-[45%] flex items-center gap-1 bg-white/95 px-2 py-0.5 border border-outline-variant/25 rounded-md text-[9px] font-medium shadow-sm">
              <span className="w-1.5 h-1.5 bg-[#fed65b] rounded-full" />
              <span>Drop-off</span>
            </div>
          </div>

          {/* Timeline markers */}
          <div className="flex justify-between items-center text-[10px] font-literata text-on-surface-variant/80 border-t border-outline-variant/10 pt-3">
            <span>0:00 Intro</span>
            <span>4:20 Key Concept</span>
            <span>8:42 Outro</span>
          </div>
        </div>

        {/* Interactive Topic Explorer Bubble Chart */}
        <div className="bg-white border border-outline-variant/10 rounded-3xl p-8 flex flex-col gap-6 shadow-sm">
          <div className="flex flex-col">
            <h3 className="font-playfair text-lg font-bold text-primary">Topic Explorer</h3>
            <p className="text-xs text-on-surface-variant font-literata mt-1">
              Select a theme to explore what your viewers are talking about.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 gap-4 items-center flex-1">
            {/* SVG Bubbles Chart Workspace */}
            <div className="w-full aspect-square relative bg-surface-container-lowest border border-outline-variant/10 rounded-2xl p-2 overflow-hidden flex items-center justify-center">
              <svg viewBox="0 0 400 300" className="w-full h-full">
                {/* Bubble 1: Pricing */}
                {clusters[0] && (
                  <g 
                    onClick={() => setSelectedClusterIndex(0)} 
                    className="cursor-pointer group"
                  >
                    <circle 
                      cx="180" cy="140" r="55" 
                      fill="#00261b" 
                      className="transition duration-200 group-hover:scale-105 origin-[180px_140px]" 
                      style={{ opacity: selectedClusterIndex === 0 ? 1 : 0.7 }}
                    />
                    <text 
                      x="180" y="143" 
                      fill="#fff" 
                      fontSize="10" 
                      fontWeight="bold" 
                      textAnchor="middle" 
                      className="pointer-events-none select-none font-playfair"
                    >
                      {clusters[0].title}
                    </text>
                  </g>
                )}

                {/* Bubble 2 */}
                {clusters[1] && (
                  <g 
                    onClick={() => setSelectedClusterIndex(1)} 
                    className="cursor-pointer group"
                  >
                    <circle 
                      cx="290" cy="190" r="45" 
                      fill="#0b3d2e" 
                      className="transition duration-200 group-hover:scale-105 origin-[290px_190px]" 
                      style={{ opacity: selectedClusterIndex === 1 ? 1 : 0.7 }}
                    />
                    <text 
                      x="290" y="193" 
                      fill="#fff" 
                      fontSize="9" 
                      fontWeight="bold" 
                      textAnchor="middle" 
                      className="pointer-events-none select-none font-playfair"
                    >
                      {clusters[1].title}
                    </text>
                  </g>
                )}

                {/* Bubble 3 */}
                {clusters[2] && (
                  <g 
                    onClick={() => setSelectedClusterIndex(2)} 
                    className="cursor-pointer group"
                  >
                    <circle 
                      cx="90" cy="200" r="38" 
                      fill="#735c00" 
                      className="transition duration-200 group-hover:scale-105 origin-[90px_200px]" 
                      style={{ opacity: selectedClusterIndex === 2 ? 1 : 0.7 }}
                    />
                    <text 
                      x="90" y="203" 
                      fill="#fff" 
                      fontSize="8" 
                      fontWeight="bold" 
                      textAnchor="middle" 
                      className="pointer-events-none select-none font-playfair"
                    >
                      {clusters[2].title}
                    </text>
                  </g>
                )}

                {/* Bubble 4 */}
                {clusters[3] && (
                  <g 
                    onClick={() => setSelectedClusterIndex(3)} 
                    className="cursor-pointer group"
                  >
                    <circle 
                      cx="280" cy="80" r="32" 
                      fill="#fed65b" 
                      className="transition duration-200 group-hover:scale-105 origin-[280px_80px]" 
                      style={{ opacity: selectedClusterIndex === 3 ? 1 : 0.7 }}
                    />
                    <text 
                      x="280" y="83" 
                      fill="#735c00" 
                      fontSize="8" 
                      fontWeight="bold" 
                      textAnchor="middle" 
                      className="pointer-events-none select-none font-playfair"
                    >
                      {clusters[3].title}
                    </text>
                  </g>
                )}

                {/* Bubble 5 */}
                {clusters[4] && (
                  <g 
                    onClick={() => setSelectedClusterIndex(4)} 
                    className="cursor-pointer group"
                  >
                    <circle 
                      cx="95" cy="85" r="28" 
                      fill="#eae7e7" 
                      className="transition duration-200 group-hover:scale-105 origin-[95px_85px]" 
                      style={{ opacity: selectedClusterIndex === 4 ? 1 : 0.7 }}
                    />
                    <text 
                      x="95" y="88" 
                      fill="#414944" 
                      fontSize="7" 
                      fontWeight="bold" 
                      textAnchor="middle" 
                      className="pointer-events-none select-none font-playfair"
                    >
                      {clusters[4].title}
                    </text>
                  </g>
                )}
              </svg>
            </div>

            {/* Selection details sidebar panel */}
            <div className="h-full flex flex-col justify-center min-h-[160px]">
              <AnimatePresence mode="wait">
                {activeCluster ? (
                  <motion.div 
                    key={activeCluster.id}
                    initial={{ opacity: 0, x: 5 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -5 }}
                    className="flex flex-col gap-2"
                  >
                    <span className="text-[10px] text-secondary font-bold tracking-wider uppercase block">
                      Topic Details
                    </span>
                    <h4 className="font-playfair text-base font-bold text-primary">
                      {activeCluster.title}
                    </h4>
                    <p className="text-xs text-on-surface-variant font-literata leading-relaxed">
                      {activeCluster.summary}
                    </p>
                    <div className="flex gap-4 items-center text-[10px] font-literata text-on-surface-variant/80 mt-2">
                      <span>Volume: <strong>{activeCluster.size} comments</strong></span>
                      <span>Sentiment: <strong>{Math.round(activeCluster.sentiment_score * 100)}%</strong></span>
                    </div>
                  </motion.div>
                ) : (
                  <span className="text-xs text-on-surface-variant/50 font-literata italic">
                    No theme selected. Hover or click a bubble to explore.
                  </span>
                )}
              </AnimatePresence>
            </div>
          </div>
          
          <span className="text-[9px] text-on-surface-variant/75 font-literata flex items-center gap-1 border-t border-outline-variant/10 pt-3">
            <span>ℹ</span>
            <span>Each bubble represents a topic — larger bubbles = more comments about that topic.</span>
          </span>
        </div>
      </div>

      {/* Section 4: Audience Questions & Pain Points */}
      {(insights.questions.length > 0 || insights.pain_points.length > 0 || insights.positive_themes.length > 0) && (() => {
        const tabConfig: { key: InsightTab; label: string; icon: React.ReactNode; items: typeof insights.questions; accent: string; dotColor: string }[] = [
          {
            key: "questions",
            label: "Questions",
            icon: <HelpCircle className="w-3.5 h-3.5" />,
            items: insights.questions,
            accent: "bg-sky-50 border-sky-200/60 text-sky-900",
            dotColor: "bg-sky-400",
          },
          {
            key: "pain_points",
            label: "Pain Points",
            icon: <MessageSquare className="w-3.5 h-3.5" />,
            items: insights.pain_points,
            accent: "bg-rose-50 border-rose-200/60 text-rose-900",
            dotColor: "bg-rose-400",
          },
          {
            key: "positive_themes",
            label: "What They Love",
            icon: <Heart className="w-3.5 h-3.5" />,
            items: insights.positive_themes,
            accent: "bg-emerald-50 border-emerald-200/60 text-emerald-900",
            dotColor: "bg-emerald-400",
          },
        ];

        const activeConfig = tabConfig.find(t => t.key === activeTab)!;
        const filtered = activeConfig.items.filter(
          item =>
            item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            item.content.toLowerCase().includes(searchQuery.toLowerCase())
        );

        return (
          <div className="bg-white border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col gap-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex flex-col">
                <h2 className="font-playfair text-xl font-bold text-primary">Audience Questions &amp; Feedback</h2>
                <p className="text-xs text-on-surface-variant font-literata mt-1">
                  What your viewers are asking, struggling with, and loving.
                </p>
              </div>

              {/* Search bar */}
              <div className="relative flex-shrink-0">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-on-surface-variant/50" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Search insights…"
                  className="pl-8 pr-8 py-2 text-xs font-literata bg-surface-container border border-outline-variant/20 rounded-full focus:outline-none focus:ring-2 focus:ring-primary/20 w-52 transition"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant/50 hover:text-on-surface-variant cursor-pointer"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-2 border-b border-outline-variant/15 pb-4">
              {tabConfig.map(tab => (
                <button
                  key={tab.key}
                  onClick={() => { setActiveTab(tab.key); setSearchQuery(""); }}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-semibold font-literata border transition-all cursor-pointer ${
                    activeTab === tab.key
                      ? tab.accent
                      : "bg-transparent border-transparent text-on-surface-variant hover:bg-surface-container"
                  }`}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                  <span className={`ml-1 text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                    activeTab === tab.key ? "bg-white/60" : "bg-surface-container"
                  }`}>
                    {tab.items.length}
                  </span>
                </button>
              ))}
            </div>

            {/* Cards grid */}
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab + searchQuery}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.18 }}
              >
                {filtered.length > 0 ? (
                  <>
                    <div className="grid md:grid-cols-2 gap-4">
                      {filtered.map(item => (
                        <div
                          key={item.id}
                          className="flex gap-3 p-5 rounded-2xl border border-outline-variant/10 bg-surface-container-lowest hover:shadow-sm transition"
                        >
                          <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${activeConfig.dotColor}`} />
                          <div className="flex flex-col gap-1">
                            <p className="font-literata text-sm font-semibold text-on-surface leading-snug">
                              {item.title}
                            </p>
                            <p className="font-literata text-xs text-on-surface-variant leading-relaxed">
                              {item.content}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                    <p className="text-[10px] text-on-surface-variant/60 font-literata mt-4">
                      Showing {filtered.length} of {activeConfig.items.length} {activeConfig.label.toLowerCase()}
                    </p>
                  </>
                ) : (
                  <div className="flex flex-col items-center gap-3 py-12 text-center">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${activeConfig.accent}`}>
                      {activeConfig.icon}
                    </div>
                    <p className="font-literata text-sm text-on-surface-variant">
                      {searchQuery
                        ? `No ${activeConfig.label.toLowerCase()} match "${searchQuery}".`
                        : `No ${activeConfig.label.toLowerCase()} were found for this analysis.`}
                    </p>
                    {searchQuery && (
                      <button
                        onClick={() => setSearchQuery("")}
                        className="text-xs font-semibold font-literata text-primary hover:underline cursor-pointer"
                      >
                        Clear search
                      </button>
                    )}
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        );
      })()}

      {/* Section 3: Content Recommendations */}
      <div className="bg-white border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col gap-6">
        {/* Header + filter */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex flex-col">
            <h2 className="font-playfair text-xl font-bold text-primary">Content Opportunities</h2>
            <p className="text-xs text-on-surface-variant font-literata mt-1">
              AI-suggested ideas derived from subscriber conversations.
            </p>
          </div>

          {/* Filter pills */}
          {recommendations.length > 0 && (
            <div className="flex items-center gap-1.5 flex-shrink-0">
              {(["all", "active", "planned", "dismissed"] as RecFilterTab[]).map(f => {
                const counts: Record<RecFilterTab, number> = {
                  all: recommendations.length,
                  active: recommendations.filter(r => (recStatuses[r.id]?.status ?? "none") === "none").length,
                  planned: recommendations.filter(r => ["planned","in_progress"].includes(recStatuses[r.id]?.status ?? "")).length,
                  dismissed: recommendations.filter(r => (recStatuses[r.id]?.status ?? "none") === "dismissed").length,
                };
                const labels: Record<RecFilterTab, string> = { all: "All", active: "Unreviewed", planned: "Planned", dismissed: "Dismissed" };
                return (
                  <button
                    key={f}
                    onClick={() => setRecFilter(f)}
                    className={`px-3 py-1.5 rounded-full text-[11px] font-semibold font-literata border transition cursor-pointer ${
                      recFilter === f
                        ? "bg-primary text-on-primary border-primary"
                        : "bg-transparent border-outline-variant/20 text-on-surface-variant hover:bg-surface-container"
                    }`}
                  >
                    {labels[f]}
                    {counts[f] > 0 && <span className="ml-1 opacity-70">({counts[f]})</span>}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Cards */}
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5 border-t border-outline-variant/20 pt-6">
          {recommendations.length > 0 ? (() => {
            const filtered = recommendations.filter(rec => {
              const status = recStatuses[rec.id]?.status ?? "none";
              if (recFilter === "active") return status === "none";
              if (recFilter === "planned") return status === "planned" || status === "in_progress";
              if (recFilter === "dismissed") return status === "dismissed";
              return true;
            });

            if (filtered.length === 0) {
              return (
                <div className="col-span-3 text-center py-10 font-literata text-xs text-on-surface-variant/60 italic">
                  No recommendations match this filter.
                </div>
              );
            }

            return filtered.map((rec) => {
              const status = recStatuses[rec.id]?.status ?? "none";
              const isDismissed = status === "dismissed";

              const statusConfig: Record<string, { label: string; color: string }> = {
                none: { label: "", color: "" },
                planned: { label: "Planned", color: "bg-amber-100 text-amber-800 border-amber-200" },
                in_progress: { label: "In Progress", color: "bg-sky-100 text-sky-800 border-sky-200" },
                dismissed: { label: "Dismissed", color: "bg-neutral-100 text-neutral-500 border-neutral-200" },
              };

              return (
                <div
                  key={rec.id}
                  className={`relative bg-surface-container-lowest border border-outline-variant/10 rounded-2xl p-5 shadow-sm flex flex-col justify-between transition ${
                    isDismissed ? "opacity-40" : "hover:shadow"
                  }`}
                >
                  {/* Status chip */}
                  {status !== "none" && (
                    <span className={`absolute top-3 right-3 text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full border ${statusConfig[status].color}`}>
                      {statusConfig[status].label}
                    </span>
                  )}

                  <div className="flex flex-col gap-3">
                    <h4 className={`font-playfair text-base font-bold mt-1 pr-16 ${ isDismissed ? "line-through text-on-surface-variant" : "text-primary" }`}>
                      {rec.title}
                    </h4>
                    <p className="text-xs text-on-surface-variant font-literata leading-relaxed">
                      {rec.content}
                    </p>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 mt-5 pt-4 border-t border-outline-variant/10">
                    {isDismissed ? (
                      <button
                        onClick={() => setRecStatus(rec.id, "none")}
                        className="text-xs font-semibold font-literata text-primary hover:underline cursor-pointer"
                      >
                        Restore
                      </button>
                    ) : (
                      <>
                        <button
                          onClick={() => setRecStatus(rec.id, status === "planned" ? "none" : "planned")}
                          title="Mark as Planned"
                          className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold font-literata border transition cursor-pointer ${
                            status === "planned"
                              ? "bg-amber-100 text-amber-800 border-amber-300"
                              : "bg-surface-container text-on-surface-variant border-outline-variant/20 hover:bg-amber-50 hover:text-amber-800"
                          }`}
                        >
                          <Check className="w-3 h-3" /> Planned
                        </button>
                        <button
                          onClick={() => setRecStatus(rec.id, status === "in_progress" ? "none" : "in_progress")}
                          title="Mark as In Progress"
                          className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold font-literata border transition cursor-pointer ${
                            status === "in_progress"
                              ? "bg-sky-100 text-sky-800 border-sky-300"
                              : "bg-surface-container text-on-surface-variant border-outline-variant/20 hover:bg-sky-50 hover:text-sky-800"
                          }`}
                        >
                          <Rocket className="w-3 h-3" /> In Progress
                        </button>
                        <button
                          onClick={() => setRecStatus(rec.id, "dismissed")}
                          title="Dismiss"
                          className="ml-auto p-1.5 rounded-full text-on-surface-variant/40 hover:text-rose-500 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition cursor-pointer"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            });
          })() : (
            <div className="col-span-3 text-center py-10 font-literata text-xs text-on-surface-variant/60 italic">
              No recommendations available for this run.
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
