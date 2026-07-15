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

export type {
  VideoDetails,
  AnalysisRun,
  TopicCluster,
  InsightItem,
  InsightsData
}