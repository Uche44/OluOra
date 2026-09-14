tiktok for developers documentation: `https://developers.tiktok.com/doc/overview`
youtube api documentation: `https://developers.google.com/youtube/v3/docs`

---

## Implementation Status (TikTok integration)

OluOra now separates **login identity** from **data-provider connections**:

- **Google** is used for sign-in only (identity scopes). It no longer requests YouTube access.
- **YouTube** and **TikTok** are connected independently from *Dashboard → Settings*.

### What is implemented

| Capability | YouTube | TikTok |
|---|---|---|
| OAuth connect/disconnect | ✅ | ✅ (Login Kit) |
| Channel + video catalog sync | ✅ | ✅ (`Display API /v2/video/list/`) |
| Comment ingestion | ✅ | ❌ No endpoint for standard apps |
| AI comment analysis | ✅ | ❌ (UI shows "coming soon") |

### TikTok specifics to remember

- Authorization page: `https://www.tiktok.com/v2/auth/authorize/`
- Token exchange/refresh: `POST https://open.tiktokapis.com/v2/oauth/token/` (`application/x-www-form-urlencoded`)
- Revoke: `POST https://open.tiktokapis.com/v2/oauth/revoke/`
- User info: `GET https://open.tiktokapis.com/v2/user/info/?fields=...`
- Video list: `POST https://open.tiktokapis.com/v2/video/list/?fields=...` (max 20/page)
- **Redirect URIs must be HTTPS and static** (no query params/fragments). Local development needs an
  HTTPS tunnel (e.g. `ngrok http 3000`) registered in the TikTok developer portal.
- Access token ~24h; refresh token ~365d. **Refresh responses may rotate the refresh token** — always persist it.
- `cover_image_url` has a **6-hour TTL**, so stored TikTok thumbnails can expire; re-sync refreshes them.
- `video.list` returns only the creator's own **public** videos; sandbox apps only work with added target users.
- Display API responses wrap results as `{"data": ..., "error": {"code": "ok"|...}}`.

### Environment variables

```
GOOGLE_YOUTUBE_REDIRECT_URI=http://localhost:3000/auth/youtube/callback
TIKTOK_CLIENT_KEY=...
TIKTOK_CLIENT_SECRET=...
TIKTOK_REDIRECT_URI=https://<tunnel-domain>/auth/tiktok/callback
```

---


OluOra — API Limitations & Workaround Strategy
What OluOra Is
OluOra is an AI-powered audience intelligence platform for creators. Its core function is to:

Authenticate creators via YouTube / TikTok OAuth
Import their videos
Fetch and analyse comment data at scale
Run NLP/AI pipelines to surface actionable audience insights
The platform's entire value chain depends heavily on reliable, scalable access to comment data from both platforms. This makes API limitations the single biggest technical risk in the project.

YouTube Data API v3 — Limitations
Quota System (The Primary Constraint)
Every Google Cloud project gets a default daily quota of 10,000 units, resetting at midnight Pacific Time.

Operation	Cost (units)
commentThreads.list (top-level comments)	1
comments.list (replies)	1
videos.list (video metadata)	1
channels.list	1
playlistItems.list (fetch all video IDs)	1
search.list	100 ⚠️
CAUTION

A single search.list call costs 100 units — the same as 100 comment fetches. Never use search.list to get a creator's video list. Use playlistItems.list (1 unit) via the channel's uploads playlist instead.

How Quickly Quota Gets Exhausted
A creator with a video that has 5,000 comments needs roughly 50 requests (at 100 comments max per page). That's 50 units for one video.

With 10,000 units/day:

You can fully process ~200 videos before running out (comment fetch only)
If you add video metadata fetches, it drops further
At scale (multi-user SaaS), 10,000 units runs out extremely fast
Pagination Constraints
maxResults is capped at 100 comments per request for commentThreads.list
Each page costs 1 unit — a video with 10,000 comments = 100 API calls = 100 units
Replies to comments require a separate comments.list call per thread
Comment Retrieval Restrictions
Comments on videos with disabled comments cannot be retrieved (API returns empty)
Comments on age-restricted or private videos require special auth scopes
The API returns comments sorted by time or relevance only — no direct keyword filtering
No way to retrieve comments posted after a specific date without filtering client-side
Authentication (OAuth 2.0)
Standard Google Sign-In with scope: https://www.googleapis.com/auth/youtube.readonly
Access tokens expire after 1 hour; refresh tokens must be stored and rotated
Users must explicitly grant OluOra access during sign-in
Quota Extension
There is no paid tier — you cannot simply buy more quota
Must submit a YouTube API Services Audit & Quota Extension Form to Google
Process is manual, subject to review, and can take weeks
Requires proving your app is Terms-of-Service compliant and quota-efficient
TikTok API — Limitations (Much More Restrictive)
The Core Problem: TikTok Has No General-Purpose Comment Read API
This is the biggest challenge for OluOra. TikTok's APIs are segmented into two worlds:

1. Login Kit / Display API (Standard Apps)
Enables OAuth login ✅
Can fetch a creator's own video list (video.list scope) ✅
Can fetch basic video metadata ✅
Cannot read comments ❌
2. Research API (Academic Use Only)
Can fetch public video comment data ✅
Endpoint: POST /v2/research/video/comment/list/
Returns: comment text, like count, reply count, timestamp
Only available to vetted academic institutions ❌
Requires formal application and approval (non-commercial use only)
Rate limit: ~1,000 requests/day, max 100 comments per request
Access tokens expire every 2 hours
Data returned can be inconsistent and incomplete (documented in academic audits)
WARNING

OluOra as a commercial SaaS product cannot use the TikTok Research API. It is reserved strictly for non-commercial academic research. This is TikTok's most critical API limitation for this project.

TikTok Standard App Restrictions Summary
Feature	Available?	Notes
OAuth login	✅	Login Kit
Fetch creator's videos	✅	video.list scope
Read comments on own videos	❌	No endpoint exists for standard apps
Read comments on public videos	❌	Research API only
Token lifetime	Short	Requires refresh token management
App review required	✅	Must pass TikTok audit before going to production
Sandbox mode	✅	For testing, but SELF_ONLY privacy restrictions
Workaround Strategies for OluOra
YouTube — Workarounds
1. Aggressive Caching (Most Important)
Store all fetched comments and video metadata in PostgreSQL. Never re-fetch data you already have.


Strategy:
- On first analysis: fetch all comments via API, store to DB
- On subsequent analyses: serve from DB, only fetch *new* comments since last sync
- Use YouTube API ETags + `If-None-Match` headers → returns 304 (no quota cost) if unchanged
2. On-Demand, Not Background Fetching
OluOra's overview doc already specifies this correctly:

"Comment retrieval begins only when analysis is requested."

Don't proactively sync all videos. Only fetch comments when the creator explicitly triggers analysis on a specific video.

3. Quota Budgeting Per User
Track each user's API usage per day
Set a per-user quota ceiling (e.g., 2,000 units/user/day on free plan)
Queue analysis jobs and spread them across the day if quota is running low
4. Use playlistItems.list for Video IDs
Each channel has an uploads playlist; use playlistItems.list to get all video IDs
Cost: 1 unit per 50 videos fetched (paginated)
Never use search.list for this — it costs 100x more
5. Apply for Quota Extension Early
Submit the quota extension form before launch, not after
Demonstrate efficient usage patterns in your application code
Plan for 50,000–100,000 units/day for a multi-user SaaS
6. Multiple API Projects (Fallback)
Create multiple Google Cloud projects with separate quotas
Route traffic across projects when one nears its limit
This is a grey-area workaround — use cautiously and only as a backup
TikTok — Workarounds (More Complex)
Option A: Build Without TikTok Comment Analysis (MVP Strategy)
For the MVP, launch with full YouTube support and limited TikTok support — authenticate TikTok users, show their video list, but display a clear message that comment analysis for TikTok is "coming soon" pending platform access.

IMPORTANT

This is the recommended path for MVP. TikTok's comment API situation is genuinely blockerish for a commercial app right now. Being honest with users is better than over-promising.

Option B: Apply for TikTok Research API Access
Apply as a research-adjacent entity (requires institutional affiliation or compelling research angle)
This is a long shot for a commercial product but worth exploring
Approval takes months and may be denied
Option C: Creator-Submitted Data
Allow TikTok creators to manually export and upload their comment data
TikTok allows users to request a data download of their own data (GDPR-style data portability)
OluOra could provide a guide on how to export comment data from TikTok Studio and upload a CSV
OluOra then runs AI analysis on the uploaded file — no API dependency

Flow:
1. Creator downloads their TikTok data (TikTok Studio → Analytics → Comments)
2. Creator uploads the CSV/JSON file to OluOra
3. OluOra processes the file through the same AI pipeline
Option D: TikTok's Commercial Content API (Monitor for Updates)
TikTok periodically updates its API offering. Watch for any future expansion of their Commercial Content API or Creator Marketplace API that may unlock comment-read access for verified SaaS partners.

Implementation Priority for OluOra

Phase 1 (MVP):
├── YouTube: Full OAuth + video list + comment fetch + AI analysis ✅
└── TikTok: OAuth login + video list only (no comment analysis yet)
Phase 2:
├── YouTube: Caching layer, quota management, on-demand sync
└── TikTok: Option C (manual upload flow) OR Research API (if approved)
Phase 3:
└── TikTok: Full comment analysis pending API access expansion
Summary Table
Concern	YouTube	TikTok
OAuth / Login	✅ Standard, well-documented	✅ Login Kit, requires app review
Fetch Creator's Videos	✅ playlistItems.list	✅ video.list
Read Comments	✅ commentThreads.list (1 unit/page)	❌ Not available for commercial apps
Daily Limit	10,000 units (extendable)	N/A for comments
Token Expiry	1 hour (refresh available)	~2 hours (Research API)
Biggest Risk	Quota exhaustion at scale	No comment API for commercial use
Main Workaround	Caching + on-demand fetch	Manual upload or YouTube-first MVP