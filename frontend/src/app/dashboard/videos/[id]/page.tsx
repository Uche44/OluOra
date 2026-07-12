"use client";

import { use, useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { authedFetch } from "@/lib/api";
import { 
  ArrowLeft,
  Play,
  RotateCw,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Lightbulb,
  MessageSquare,
  HelpCircle,
  Clock,
  Heart
} from "lucide-react";

interface VideoDetails {
  id: string;
  youtube_video_id: string;
  title: string;
  description: string;
  thumbnail_url: string;
  published_at: string;
  view_count: number;
  like_count: number;
  comment_count: number;
  sync_status: string;
}

interface AnalysisRun {
  id: string;
  status: string;
  comments_analyzed: number;
  error_message: string | null;
}

interface TopicCluster {
  id: string;
  title: string;
  summary: string;
  size: number;
  sentiment_score: number;
}

interface InsightItem {
  id: string;
  type: string;
  title: string;
  content: string;
}

interface InsightsData {
  questions: InsightItem[];
  pain_points: InsightItem[];
  positive_themes: InsightItem[];
}

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

  // Fetch functions
  const loadData = useCallback(async () => {
    setLoading(true);
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
          const recsData = await recsRes.json();
          setRecommendations(recsData);
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
          <button onClick={loadData} className="px-5 py-2 rounded-full bg-amber-700 text-white font-semibold hover:bg-amber-800 transition cursor-pointer">
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
          {isRunning ? "Analyzing Video Comments..." : "Editorial Intelligence Pending"}
        </h1>
        
        <p className="text-sm font-literata text-on-surface-variant leading-relaxed">
          {isRunning 
            ? "OluOra is currently fetching YouTube comments, generating semantic embeddings, and clustering viewer topics. This takes less than a minute."
            : "Trigger an AI editorial report to automatically map viewer segments, emotional sentiments, FAQs, and content suggestions."}
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

      {/* Section 1: Audience Interest Clusters */}
      <div className="flex flex-col gap-5">
        <h2 className="font-playfair text-xl font-bold text-primary border-b border-outline-variant/20 pb-3">
          Audience Interest Clusters
        </h2>
        
        <div className="grid lg:grid-cols-3 gap-6 items-stretch">
          {/* AI Editorial Summary Card */}
          <div className="bg-[#0b3d2e] rounded-3xl p-8 text-white flex flex-col justify-between min-h-[280px]">
            <div className="flex flex-col gap-4">
              <span className="text-[10px] uppercase font-semibold tracking-wider text-on-primary-container inline-flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Editorial AI Summary</span>
              </span>
              <p className="font-playfair text-lg italic leading-relaxed mt-2 font-medium">
                &ldquo;{clusters.length > 0 
                  ? `This audience is primarily interested in ${clusters[0].title.toLowerCase()} and ${clusters[1]?.title.toLowerCase() || 'tutorials'}, indicating key clusters of viewer interest.`
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
              Select clusters to explore specific viewer discussion details.
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
                    No cluster selected. Hover or click bubble nodes.
                  </span>
                )}
              </AnimatePresence>
            </div>
          </div>
          
          <span className="text-[9px] text-on-surface-variant/75 font-literata flex items-center gap-1 border-t border-outline-variant/10 pt-3">
            <span>ℹ</span>
            <span>Clusters are size-mapped by comment mention frequency.</span>
          </span>
        </div>
      </div>

      {/* Section 3: Content Opportunities Grid */}
      <div className="bg-white border border-outline-variant/10 rounded-3xl p-8 shadow-sm flex flex-col gap-6">
        <div className="flex flex-col">
          <h2 className="font-playfair text-xl font-bold text-primary">Content Opportunities</h2>
          <p className="text-xs text-on-surface-variant font-literata mt-1">
            Actionable outlines and ideas derived from subscriber suggestions.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 border-t border-outline-variant/20 pt-6">
          {recommendations.length > 0 ? (
            recommendations.slice(0, 3).map((rec, idx) => {
              const isFirst = idx === 0;
              const isSecond = idx === 1;
              
              let badge = "RECOMMENDED NEXT";
              let badgeBg = "bg-amber-100/50 text-amber-900 border-amber-200/50";
              
              if (isSecond) {
                badge = "EDUCATIONAL GAP";
                badgeBg = "bg-emerald-100/50 text-emerald-900 border-emerald-200/50";
              } else if (idx === 2) {
                badge = "TREND ALERT";
                badgeBg = "bg-indigo-100/50 text-indigo-900 border-indigo-200/50";
              }

              return (
                <div 
                  key={rec.id} 
                  className="bg-surface-container-lowest border border-outline-variant/10 rounded-2xl p-5 shadow-sm hover:shadow transition flex flex-col justify-between"
                >
                  <div className="flex flex-col gap-3">
                    <span className={`text-[9px] font-bold tracking-wider px-2 py-0.5 rounded-full border self-start ${badgeBg}`}>
                      {badge}
                    </span>
                    <h4 className="font-playfair text-base font-bold text-primary mt-1">
                      {rec.title}
                    </h4>
                    <p className="text-xs text-on-surface-variant font-literata leading-relaxed">
                      {rec.content}
                    </p>
                  </div>

                  <button className="flex items-center gap-1.5 text-xs font-semibold font-literata text-[#735c00] hover:underline mt-6 self-start cursor-pointer">
                    <span>{isFirst || isSecond ? "Generate Script Outline" : "Analyze Topic Search"}</span>
                    <span>→</span>
                  </button>
                </div>
              );
            })
          ) : (
            <div className="col-span-3 text-center py-10 font-literata text-xs text-on-surface-variant/60 italic">
              No recommendations available for this run.
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
