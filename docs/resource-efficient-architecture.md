OluNdi — Resource-Efficient System Design

Scope: YouTube-only MVP. Every design decision here is made to minimise cost at each layer while keeping the system maintainable and scalable.

The Three Cost Centres
Before designing anything, understand where money actually gets spent:

Cost Centre	What Eats the Budget	Severity
YouTube API Quota	Every commentThreads.list call	🔴 Critical
AI / LLM inference	Embeddings + clustering + GPT calls per analysis	🔴 Critical
Compute & Database	Server size, DB queries, memory usage	🟡 Moderate
Everything below targets all three simultaneously.

Layer 1 — YouTube API Quota Efficiency
1.1 The Golden Rule: Store Everything, Re-fetch Nothing
The moment you receive any data from the YouTube API, persist it immediately. The API is the bottleneck; the database is cheap.


YouTube API (expensive)
      ↓
  PostgreSQL (cheap, fast)
      ↓
  Application Logic (serves from DB wherever possible)
1.2 Use the Right Endpoints
Task	Wrong (Expensive)	Right (Cheap)
Get creator's video IDs	search.list (100 units)	playlistItems.list (1 unit)
Get video metadata	videos.list?id=v1,v2,...,v50 one by one	Batch up to 50 IDs per request (1 unit)
Check if video has new comments	Re-fetch all comments	Use ETag header — costs 0 units if unchanged
Get top-level comments	commentThreads.list (1 unit/page)	Same, but set maxResults=100 always
1.3 Incremental Comment Sync (Delta Fetching)
Never re-fetch all comments from scratch for a video you've already analysed.

How it works:

Store the publishedAt timestamp of the most recent comment you fetched, per video, in the DB
On subsequent fetches, use commentThreads.list with order=time and stop pagination as soon as you hit a comment older than your stored timestamp
Only the new comments since last sync are fetched and appended to DB

Video first analysed:  fetch ALL 5,000 comments → 50 API calls
Video re-analysed 2 weeks later: fetch only 300 NEW comments → 3 API calls
Savings: 94% fewer API calls on repeat analyses
1.4 ETag-Based Revalidation
The YouTube API returns an ETag header on every response. Store it.

python

# Before fetching a new page of comments:
headers = {"If-None-Match": stored_etag}
response = youtube_client.get(url, headers=headers)
if response.status_code == 304:
    # Data hasn't changed — costs 0 quota units
    return cached_data
# Otherwise, update cache with new ETag
store_etag(new_etag)
1.5 Quota Tracking in the Database
Track every API call made and its unit cost.

sql

CREATE TABLE api_quota_usage (
    id          SERIAL PRIMARY KEY,
    user_id     UUID REFERENCES users(id),
    endpoint    VARCHAR(100),        -- e.g. 'commentThreads.list'
    units_used  INTEGER,
    called_at   TIMESTAMPTZ DEFAULT NOW()
);
Before any API call, check the day's running total. If the global or per-user limit is approaching, queue the job instead of executing immediately.

1.6 Quota Budget Allocation
User Plan	Daily Quota Budget	Max Analyses/Day
Free	1,000 units	~3–5 videos
Pro	5,000 units	~20–30 videos
Agency	10,000 units	~100+ videos
Allocating budgets per user means a single heavy user can't drain the entire project quota.

Layer 2 — The Analysis Job Pipeline (Async, Not Blocking)
2.1 Why This Matters for Cost
If you run analysis synchronously on the HTTP request, you:

Tie up a server process for minutes while fetching thousands of comments
Have no retry mechanism if the API times out
Cannot batch or prioritise jobs efficiently
Burn quota in a chaotic, uncontrolled way
Solution: a persistent job queue backed by PostgreSQL.

2.2 Job Queue Schema
sql

CREATE TYPE job_status AS ENUM ('queued', 'running', 'done', 'failed');
CREATE TABLE analysis_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    video_id        VARCHAR(50),
    status          job_status DEFAULT 'queued',
    priority        INTEGER DEFAULT 5,       -- lower = higher priority
    attempts        INTEGER DEFAULT 0,
    max_attempts    INTEGER DEFAULT 3,
    last_error      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    result_id       UUID REFERENCES analyses(id)
);
2.3 The Analysis Pipeline Flow

[1] Creator clicks "Analyse Video"
        ↓
[2] API inserts row into analysis_jobs (status=queued)
    → Returns job_id to frontend immediately (202 Accepted)
        ↓
[3] Background worker picks up job (SKIP LOCKED pattern)
        ↓
[4] Check DB: do we have cached comments?
    ├── YES (< 24h old): skip YouTube API call entirely
    └── NO / STALE: fetch from YouTube API (incremental delta only)
        ↓
[5] Run AI pipeline on comments (batched, not one-by-one)
        ↓
[6] Store results in analyses table
        ↓
[7] Update job status → done
        ↓
[8] Frontend polls /jobs/{job_id} or receives WebSocket push
2.4 Worker Implementation (PostgreSQL SKIP LOCKED)
This pattern gives you reliable job processing with zero extra infrastructure (no Redis, no Celery) for the MVP.

python

async def pick_up_job():
    """Atomically claim one job from the queue."""
    async with db.transaction():
        job = await db.fetchrow("""
            SELECT * FROM analysis_jobs
            WHERE status = 'queued'
              AND attempts < max_attempts
            ORDER BY priority ASC, created_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
        """)
        if job:
            await db.execute("""
                UPDATE analysis_jobs
                SET status = 'running',
                    started_at = NOW(),
                    attempts = attempts + 1
                WHERE id = $1
            """, job['id'])
    return job
Why SKIP LOCKED? Multiple worker processes can run simultaneously. SKIP LOCKED ensures two workers never accidentally claim the same job.

Layer 3 — Database Caching Strategy
3.1 The Comment Cache
sql

CREATE TABLE comments (
    id              VARCHAR(100) PRIMARY KEY,  -- YouTube comment ID
    video_id        VARCHAR(50) NOT NULL,
    author_name     VARCHAR(200),
    text            TEXT NOT NULL,
    like_count      INTEGER DEFAULT 0,
    reply_count     INTEGER DEFAULT 0,
    published_at    TIMESTAMPTZ,
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),
    is_reply        BOOLEAN DEFAULT FALSE,
    parent_id       VARCHAR(100)
);
CREATE INDEX idx_comments_video_id ON comments(video_id);
CREATE INDEX idx_comments_published_at ON comments(published_at);
3.2 Cache Freshness Logic

Analysis requested for Video X
        ↓
Check: when was the last comment fetch for Video X?
        ↓
├── < 6 hours ago → serve analysis from cached comments, no API call
├── 6–24 hours ago → serve previous analysis, trigger background refresh
└── > 24 hours ago → force fresh fetch (delta sync only, not full re-fetch)
The 6-hour window is tunable per plan tier — Pro users can get fresher data.

3.3 Video Metadata Cache
sql

CREATE TABLE videos (
    youtube_id      VARCHAR(50) PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    title           TEXT,
    thumbnail_url   TEXT,
    view_count      BIGINT,
    like_count      BIGINT,
    comment_count   INTEGER,
    published_at    TIMESTAMPTZ,
    metadata_fetched_at  TIMESTAMPTZ,
    last_comment_sync    TIMESTAMPTZ,
    latest_comment_at    TIMESTAMPTZ    -- used for delta sync cursor
);
Video metadata (title, thumbnail, counts) rarely changes. Cache it for 24 hours and only re-fetch on dashboard load if the cache is stale.

3.4 Analysis Result Caching
Store the AI analysis output. If a creator requests analysis on the same video within a configurable window and no new comments exist, serve the cached analysis — zero API calls, zero AI cost.

sql

CREATE TABLE analyses (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id        VARCHAR(50) REFERENCES videos(youtube_id),
    user_id         UUID REFERENCES users(id),
    comment_count   INTEGER,             -- how many comments were processed
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    is_fresh        BOOLEAN DEFAULT TRUE,
    -- Results stored as JSONB for flexibility
    topic_clusters  JSONB,
    top_questions   JSONB,
    pain_points     JSONB,
    positive_themes JSONB,
    content_suggestions JSONB,
    sentiment_summary JSONB
);
Layer 4 — AI Pipeline Cost Efficiency
4.1 The Cost Breakdown
For a video with 5,000 comments, here's what the naive approach costs vs. the efficient approach:

Step	Naive	Efficient
Embeddings	5,000 × individual API calls	Batch 5,000 in one API call
Clustering	No deduplication	Remove duplicates/spam first, cluster only ~2,000 unique comments
LLM summarisation	Send all 5,000 comments to GPT	Send only cluster centroids (top 10–20 representative comments per topic)
Re-analysis	Full re-run every time	Cache embeddings; only re-embed new comments
4.2 Pre-Processing Before AI (Reduces Token Count)
Run this cheap, local filtering pipeline before any paid AI call:


Step 1: Deduplication
   → Remove exact duplicate comments (simple hashing, free)
   → Remove near-duplicates ("great video" × 200 → keep 1)
Step 2: Spam Filtering
   → Remove comments <5 words
   → Remove emoji-only comments
   → Remove promotional/bot patterns (regex, free)
Step 3: Language Detection
   → If running English-only analysis, discard non-English comments
   → Use langdetect library (free, local)
Result: Often reduces 5,000 comments → 1,500–2,000 meaningful ones
Cost Reduction: 60–70% fewer tokens to embed and cluster
4.3 Embedding Strategy: Batch Everything
python

# WRONG — 5,000 separate API calls
for comment in comments:
    embedding = openai.embed(comment.text)
# RIGHT — 1 API call (or a few batches of 2,048)
texts = [c.text for c in filtered_comments]
embeddings = openai.embed(texts, batch_size=2048)
Cost: OpenAI text-embedding-3-small = $0.02 per 1M tokens. 5,000 comments × ~20 tokens avg = 100,000 tokens = $0.002 per video analysis. Negligible.

4.4 Store Embeddings — Never Recompute Them
sql

ALTER TABLE comments ADD COLUMN embedding VECTOR(1536);  -- pgvector extension
Once a comment has an embedding, never recompute it. On re-analysis, only new comments get embedded. All clustering uses stored vectors.

4.5 LLM (GPT) Calls — The Expensive Step
GPT-4o costs ~$5/1M input tokens. Sending 5,000 comments directly to GPT for every analysis would cost ~$0.50–$1.00 per analysis. At scale, that adds up fast.

The solution: only send cluster representatives, not all comments.


1. Embed all comments (cheap)
2. Cluster into 5–10 topic groups (local, free — use sklearn KMeans)
3. From each cluster, pick the 3–5 comments closest to the centroid
4. Send ONLY those ~30–50 comments to GPT for labelling and insight generation
5. GPT returns: cluster names, key questions, pain points, recommendations
Token reduction: 5,000 comments → ~50 representative samples = 99% reduction
Cost: from ~$0.50 to ~$0.005 per analysis
4.6 GPT Prompt Design for Cost
One well-structured prompt that returns structured JSON is far cheaper than multiple back-and-forth calls.

python

ANALYSIS_PROMPT = """
You are an audience intelligence analyst. Given the following comment clusters from a YouTube video,
return a structured JSON analysis.
Clusters:
{cluster_data}
Return JSON with these keys:
- topic_clusters: [{name, description, percentage, key_phrases}]
- top_questions: [string]
- pain_points: [string]
- positive_themes: [string]
- content_recommendations: [string]
Be concise. Return only valid JSON.
"""
One call. One response. One parse. No retries needed if structured correctly.

Layer 5 — API Design Patterns for Efficiency
5.1 HTTP Caching Headers on Your Own API
Send cache headers on all stable responses so the browser (and any CDN) doesn't hit your backend unnecessarily.

python

# Video list endpoint — data changes rarely
@router.get("/videos")
async def get_videos(response: Response):
    response.headers["Cache-Control"] = "private, max-age=300"  # 5 min
    return videos
# Analysis result — immutable once computed
@router.get("/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, response: Response):
    response.headers["Cache-Control"] = "private, max-age=3600"  # 1 hour
    return analysis
5.2 Partial Responses / Field Filtering
The YouTube API uses part parameters to limit response size. Mirror this in your own API — let the frontend request only the fields it needs.


GET /videos?fields=youtube_id,title,thumbnail_url,comment_count
This reduces payload size, serialization time, and database query cost (only SELECT the needed columns).

5.3 Pagination on All List Endpoints
Never return unbounded lists. Always paginate.

python

@router.get("/videos")
async def get_videos(
    page: int = 1,
    per_page: int = Query(default=20, le=50)
):
    offset = (page - 1) * per_page
    videos = await db.fetch(
        "SELECT ... FROM videos WHERE user_id = $1 LIMIT $2 OFFSET $3",
        user_id, per_page, offset
    )
    return {"data": videos, "page": page, "per_page": per_page}
5.4 Async I/O Throughout
All I/O in FastAPI should be async. A single async worker can handle hundreds of concurrent database queries without blocking.

python

# Correct — non-blocking
async def fetch_comments(video_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(youtube_url, params=params)
    return response.json()
If any single operation blocks (e.g., CPU-heavy clustering), run it in a thread pool:

python

from fastapi.concurrency import run_in_threadpool
clusters = await run_in_threadpool(run_kmeans_clustering, embeddings)
Layer 6 — Infrastructure Right-Sizing
6.1 Start Small, Scale Intentionally
Component	MVP Spec	Scale-Up Trigger
API server	1× 1GB RAM VPS (e.g., Hetzner CX11)	> 50 concurrent users
Database	Managed PostgreSQL, 1 CPU / 2GB RAM	Storage > 10GB or slow queries
Workers	2 background worker processes on same box	Job queue depth > 100 consistently
Redis	Not needed for MVP	Job volume > 500/day or need scheduling
AI inference	OpenAI API (no server needed)	Bill > $200/month (then evaluate self-hosted)
6.2 pgvector Instead of a Separate Vector DB
For MVP, do not spin up Pinecone, Weaviate, or Qdrant. Use the pgvector PostgreSQL extension. It runs inside your existing database and handles semantic search and clustering efficiently up to millions of vectors.

sql

-- Install once
CREATE EXTENSION IF NOT EXISTS vector;
-- Add to comments table
ALTER TABLE comments ADD COLUMN embedding VECTOR(1536);
-- Find semantically similar comments
SELECT text, embedding <=> $1 AS distance
FROM comments
WHERE video_id = $2
ORDER BY distance ASC
LIMIT 10;
This saves $70–$200/month on a separate vector database service.

6.3 Connection Pooling
Use PgBouncer or SQLAlchemy's built-in pool to reuse database connections. Without this, each API request opens a new DB connection — PostgreSQL handles ~100 simultaneous connections before degrading.

python

# SQLAlchemy async pool config
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,        # keep 10 connections open
    max_overflow=20,     # allow 20 more under load
    pool_pre_ping=True   # health-check before use
)
Summary: Cost Reduction Decision Tree

Creator requests analysis
        │
        ▼
┌───────────────────────────────────────────┐
│ Have we analysed this video in last 6h?   │
│ AND are there no new comments since?      │
└───────────────────────────────────────────┘
        │ YES                    │ NO
        ▼                        ▼
Return cached analysis    Fetch delta comments only
(0 API calls, 0 AI cost)  (not full re-fetch)
                                 │
                                 ▼
                     Pre-process: dedupe, spam filter,
                     language filter
                     (local, free, reduces load 60–70%)
                                 │
                                 ▼
                     Embed only NEW comments
                     (batch call, ~$0.002 per 5k comments)
                                 │
                                 ▼
                     Cluster using stored + new embeddings
                     (local sklearn, free)
                                 │
                                 ▼
                     Send ~30–50 cluster reps to GPT
                     (~$0.005 per analysis)
                                 │
                                 ▼
                     Store result, serve to creator
Target Economics at Scale
Scale	Monthly API Quota	Monthly AI Cost	Monthly Infra	Total
50 users, 5 analyses each	Default 10k/day (free)	~$5	~$15	~$20
500 users, 10 analyses each	Extended quota (free, audited)	~$50	~$40	~$90
5,000 users	Extended + multiple projects	~$400	~$150	~$550
Revenue break-even at 5,000 users would require only ~$0.11/user/month in infrastructure costs — easily covered even by a low-ticket free plan.