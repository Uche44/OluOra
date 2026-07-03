# SYSTEM_DESIGN.md (Part 1)

# OluOra System Design

Version: 1.0 (MVP)

---

# 1. Purpose

This document defines the architectural principles, resource management strategy, and system design decisions for OluOra.

Its purpose is to ensure every engineer and AI coding agent builds the platform consistently, efficiently, and with scalability in mind.

This document is the engineering source of truth for:

* system architecture
* request lifecycle
* data lifecycle
* ownership boundaries
* resource management
* scalability strategy
* cost optimization

---

# 2. Engineering Philosophy

OluOra follows several core engineering principles.

## 2.1 Minimize External API Calls

External APIs are slow, rate-limited, and expensive.

Never fetch data that already exists locally.

Every external request should have a clear purpose.

Priority:

1. Database
2. Cache
3. External API

Never reverse this order.

---

## 2.2 Store Expensive Computation

Comment analysis is expensive.

AI generation is expensive.

Embeddings are expensive.

Never regenerate results if they already exist.

Persist every expensive computation.

---

## 2.3 Compute Only When Necessary

Nothing should be analyzed automatically.

Analysis happens only when:

* user explicitly requests it
* cached analysis has expired
* user manually refreshes

Avoid background work that provides little user value.

---

## 2.4 Design for Horizontal Scaling

No service should rely on local memory.

All application instances should be stateless.

Persistent state belongs in:

* PostgreSQL
* Object Storage
* Cache

Never inside application memory.

---

## 2.5 Every Resource Has One Owner

Every record in the system belongs to another resource.

Ownership prevents:

* orphaned records
* unauthorized access
* inconsistent deletes

---

# 3. High-Level Architecture

```
                        +----------------------+
                        |     Web Browser      |
                        +----------+-----------+
                                   |
                                   |
                          HTTPS / REST API
                                   |
                     +-------------v-------------+
                     |        Next.js App        |
                     +-------------+-------------+
                                   |
                        Authenticated Requests
                                   |
                     +-------------v-------------+
                     |        FastAPI API        |
                     +------+------+-------------+
                            |      |
               Business Logic      |
                            |      |
                            |      |
         +------------------+      +----------------------+
         |                                         |
         |                                         |
+--------v---------+                     +---------v---------+
| PostgreSQL       |                     | AI Service Layer  |
|                  |                     |                   |
| Users            |                     | Embeddings        |
| Videos           |                     | Clustering        |
| Comments         |                     | Insight Generator |
| Analyses         |                     | Recommendations   |
+------------------+                     +---------+---------+
                                                  |
                                                  |
                                        AI Provider / Models
```

---

## Responsibilities

### Frontend

Responsible for:

* authentication
* dashboard rendering
* video browsing
* displaying insights
* user interactions

Never performs analysis.

---

### Backend

Responsible for:

* authentication
* authorization
* YouTube communication
* business logic
* AI orchestration
* database operations

---

### Database

Responsible for persistent storage.

Stores:

* users
* connected accounts
* videos
* comments
* analyses
* insights
* recommendations

---

### AI Layer

Responsible for:

* preprocessing
* embeddings
* clustering
* summarization
* recommendations

The frontend never communicates directly with AI providers.

---

# 4. Resource Ownership

Every entity belongs to another entity.

```
User
│
├── Social Account
│      │
│      ├── Videos
│      │      │
│      │      ├── Comments
│      │      │
│      │      ├── Analysis Jobs
│      │      │
│      │      └── Analyses
│      │               │
│      │               ├── Insights
│      │               ├── Questions
│      │               ├── Topic Clusters
│      │               └── Recommendations
```

---

## Ownership Rules

### User

Owns:

* connected accounts
* preferences
* analyses

Deleting a user removes every owned resource.

---

### Social Account

Owns:

* imported videos
* synchronization metadata

One user may connect multiple accounts in the future.

MVP supports one YouTube account.

---

### Video

Owns:

* comments
* analyses

Videos never own users directly.

Ownership is always:

Video → Social Account → User

---

### Analysis

Owns:

* insights
* questions
* recommendations
* clusters

Deleting an analysis removes every generated artifact.

Comments remain intact.

---

# Ownership Constraints

Every request must verify ownership.

Example:

User requests

```
GET /videos/123
```

The backend must verify:

```
Video

↓

Social Account

↓

User

↓

JWT User
```

Never trust IDs received from the frontend.

---

# 5. High-Level Request Lifecycle

Every request follows the same pipeline.

```
Browser

↓

Middleware

↓

Authentication

↓

Authorization

↓

Validation

↓

Business Logic

↓

Database

↓

Response Formatter

↓

JSON Response
```

---

## Step 1

Authentication

Verify:

* JWT
* expiration
* signature

If invalid:

401 Unauthorized

---

## Step 2

Authorization

Verify ownership.

Example:

Video belongs to authenticated user.

If not:

403 Forbidden

---

## Step 3

Validation

Validate:

* IDs
* query parameters
* payload

Reject invalid requests immediately.

---

## Step 4

Business Logic

Business rules execute here.

Examples:

* connect YouTube
* fetch videos
* request analysis

---

## Step 5

Database

Read or write data.

Prefer existing records over external requests.

---

## Step 6

Response

Serialize using Pydantic response models.

Never expose database models directly.

---

# Example Request

```
User clicks Analyze
        │
        ▼
POST /videos/{id}/analyze
        │
        ▼
Validate JWT
        │
        ▼
Verify ownership
        │
        ▼
Check previous analysis
        │
        ▼
Analysis exists?
       / \
     Yes  No
      │    │
      │    ▼
      │ Fetch comments
      │    │
      │ Clean comments
      │    │
      │ AI processing
      │    │
      │ Store results
      │
      ▼
Return analysis
```

---

# 6. Data Lifecycle

Every resource has a lifecycle.

Nothing lives forever.

---

## User Lifecycle

```
User signs in

↓

User created

↓

YouTube connected

↓

Videos imported

↓

Uses platform

↓

Disconnects account

↓

Data archived

↓

Account deleted
```

---

## Video Lifecycle

```
Imported

↓

Metadata stored

↓

Displayed in dashboard

↓

Selected for analysis

↓

Comments fetched

↓

Analysis generated

↓

Insights displayed

↓

Periodic refresh
```

---

## Comment Lifecycle

```
Fetched

↓

Normalized

↓

Deduplicated

↓

Stored

↓

Embedded

↓

Clustered

↓

Referenced by insights

↓

Archived
```

Comments should never be embedded twice unless the text changes.

---

## Analysis Lifecycle

```
Requested

↓

Queued

↓

Running

↓

Completed

↓

Displayed

↓

Cached

↓

Refreshed

↓

Archived
```

Analysis is immutable.

Refreshing creates a new analysis version rather than modifying the previous one.

---

# 7. Analysis Versioning

Every analysis records how it was generated.

Store:

* analysis_version
* embedding_model
* llm_model
* prompt_version
* clustering_algorithm
* generated_at

Example

```
Analysis

↓

Version 1.0

↓

text-embedding-3-small

↓

GPT-4.1 Mini

↓

Prompt v2

↓

HDBSCAN

↓

2026-07-03
```

Historical analyses should always remain reproducible.

---

# 8. Engineering Rules

The following rules are mandatory.

## Resource Rules

* Every database record must have one owner.
* Never expose resources belonging to another user.
* Never trust frontend identifiers.
* Every API must validate ownership.

---

## Request Rules

* Authenticate first.
* Authorize second.
* Validate third.
* Execute business logic fourth.
* Query the database fifth.
* Return serialized responses last.

---

## Lifecycle Rules

* Never delete comments during refresh.
* Never overwrite analyses.
* Create new analysis versions.
* Archive old data instead of destroying it whenever practical.

---

## Architecture Rules

* Frontend never communicates directly with AI providers.
* AI providers never communicate with the database.
* Business logic always lives in backend services.
* Controllers should remain thin.
* Database models must never be returned directly to clients.

---

# Future Evolution

As OluOra grows, this architecture will evolve to include:

* Background workers
* Distributed job queues
* Vector database
* Redis caching
* Scheduled synchronization
* Webhook-driven updates
* Multi-platform ingestion
* Real-time notifications

The principles defined in this document should remain unchanged regardless of infrastructure changes.

# SYSTEM_DESIGN.md (Part 2)

# 9. Storage Strategy

## Overview

OluOra is designed around one principle:

> **Store expensive data once. Reuse it many times.**

Storage should prioritize:

* Low operational cost
* Fast reads
* Minimal duplication
* Easy maintenance
* Future scalability

The database should always be considered the primary source of truth.

---

## Storage Categories

### 1. User Data

Purpose

Stores authentication and account information.

Examples

* User
* Social Account
* Preferences
* OAuth Tokens

Characteristics

* Small
* Frequently read
* Rarely updated

---

### 2. Metadata

Purpose

Stores lightweight YouTube information.

Examples

* Video title
* Thumbnail
* Publish date
* View count
* Like count
* Comment count

Characteristics

* Read frequently
* Updated occasionally
* Never AI-generated

---

### 3. Raw Data

Purpose

Stores imported comments.

Examples

* Comment text
* Author
* Published time
* Like count

Characteristics

* Large
* Append-heavy
* Rarely modified

Comments are immutable once stored.

---

### 4. AI Data

Purpose

Stores outputs from expensive AI processing.

Examples

* Topic clusters
* Questions
* Recommendations
* Sentiment
* Summary
* Confidence scores

Characteristics

* Expensive to generate
* Frequently viewed
* Never regenerate unless requested

---

### 5. Analytics

Purpose

Stores historical analysis information.

Examples

* Analysis date
* Processing time
* AI cost
* Analysis version

Characteristics

* Small
* Append only

---

# Storage Rules

Always normalize relational data.

Never duplicate:

* Users
* Videos
* Accounts

Duplicate only when performance benefits outweigh storage costs.

---

# Database Relationships

```text
User
 └── SocialAccount
        └── Video
              ├── Comment
              ├── Analysis
              │      ├── Insight
              │      ├── Question
              │      ├── Recommendation
              │      └── TopicCluster
              └── SyncMetadata
```

---

# Storage Priorities

Priority Order

1. PostgreSQL
2. Cache
3. External APIs

Never use YouTube as the primary data source after import.

---

# Large Objects

Avoid storing large blobs in PostgreSQL.

Future assets such as:

* exports
* reports
* PDFs

should live in object storage.

Store only references inside PostgreSQL.

---

# Data Retention

Videos

Keep indefinitely.

Comments

Keep unless user deletes account.

Analyses

Keep all versions.

Insights

Keep permanently.

Jobs

Delete after retention period.

Logs

Rotate automatically.

---

# Archiving

Old analyses should never be deleted.

Instead:

Active Analysis

↓

Historical Archive

↓

Cold Storage (future)

---

# 10. Caching Strategy

## Purpose

Caching exists to reduce:

* AI costs
* Database load
* API requests
* User waiting time

---

## Cache Hierarchy

```text
Browser

↓

CDN (Future)

↓

Application Cache

↓

Database

↓

External APIs
```

---

## MVP

For the MVP:

No Redis.

Use PostgreSQL as the cache.

Store:

* imported videos
* imported comments
* completed analyses

If data already exists:

Return immediately.

---

## Future

When traffic increases:

Introduce Redis.

Redis stores:

* dashboard summaries
* user sessions
* frequently viewed analyses
* expensive aggregate queries

---

# Cache Rules

Never cache:

OAuth tokens

Passwords

Sensitive credentials

Always cache:

Video metadata

Completed analyses

Dashboard metrics

Insight summaries

---

# Cache Expiration

Video Metadata

Refresh every 24 hours.

Comments

Refresh only when requested.

Analysis

Never expires automatically.

New analysis requires explicit refresh.

---

# Cache Invalidation

Invalidate when:

User requests refresh

↓

Fetch latest comments

↓

Generate new analysis

↓

Replace active version

↓

Archive previous version

---

# 11. Job Processing

## Philosophy

Long-running work should never block HTTP requests.

Every expensive operation becomes a job.

---

## MVP

MVP executes jobs synchronously.

Sequence

Request

↓

Validate

↓

Fetch comments

↓

Analyze

↓

Store

↓

Return

---

This keeps deployment simple.

---

## Future

Introduce background workers.

Architecture

```text
Request

↓

Create Job

↓

Queue

↓

Worker

↓

AI Processing

↓

Database

↓

Completed
```

---

# Job States

```text
Queued

↓

Running

↓

Completed
```

Failures

```text
Running

↓

Failed

↓

Retry

↓

Completed

OR

Permanent Failure
```

---

# Job Types

Video Import

Comment Sync

Comment Analysis

Insight Generation

Recommendation Generation

Historical Refresh

---

# Retry Policy

Retry only for transient failures.

Examples

Network timeout

API unavailable

Rate limit

Never retry:

Invalid OAuth

Deleted video

Permission denied

Malformed request

---

# Retry Strategy

Attempt 1

↓

5 seconds

↓

Attempt 2

↓

30 seconds

↓

Attempt 3

↓

2 minutes

↓

Permanent Failure

---

# Job Logging

Record:

Job ID

User ID

Video ID

Duration

Status

Error

Retry Count

AI Cost

---

# Job Ownership

Every job belongs to:

User

↓

Video

↓

Analysis

Jobs should never exist without an owner.

---

# 12. AI Pipeline

## Goal

Convert thousands of comments into actionable audience intelligence.

---

## Pipeline Overview

```text
Comments

↓

Cleaning

↓

Normalization

↓

Language Detection

↓

Spam Removal

↓

Deduplication

↓

Embeddings

↓

Topic Clustering

↓

Question Extraction

↓

Insight Generation

↓

Recommendations

↓

Database
```

---

## Stage 1

Comment Retrieval

Retrieve comments from YouTube.

Store immediately.

Never request twice unless refreshing.

---

## Stage 2

Cleaning

Remove:

HTML

Emoji noise

Repeated whitespace

Broken formatting

URLs (optional)

---

## Stage 3

Normalization

Normalize:

Case

Unicode

Whitespace

Common abbreviations

---

## Stage 4

Language Detection

Identify language.

Future versions may support multilingual analysis.

MVP:

English only.

---

## Stage 5

Spam Filtering

Remove:

Bots

Duplicate comments

Advertisements

Repeated text

Low-value noise

---

## Stage 6

Embeddings

Generate semantic embeddings.

Store permanently.

Never regenerate unless model changes.

---

## Stage 7

Topic Clustering

Group semantically similar comments.

Example

Pricing

Beginner Questions

Setup Issues

Feature Requests

Praise

Criticism

---

## Stage 8

Question Extraction

Extract recurring audience questions.

Rank by frequency.

Store independently.

---

## Stage 9

Insight Generation

Generate:

Topic percentages

Audience summaries

Pain points

Opportunities

Confidence scores

---

## Stage 10

Recommendations

Produce actionable recommendations.

Examples

Create pricing guide

Record beginner tutorial

Address setup confusion

Publish FAQ

---

# AI Cost Tracking

Every analysis records:

Input Tokens

Output Tokens

Embedding Tokens

LLM Model

Embedding Model

Prompt Version

Cost

Duration

Comments Processed

---

# AI Versioning

Store:

Analysis Version

Prompt Version

Embedding Model

LLM Model

Clustering Algorithm

This enables reproducibility.

---

# 13. API Design

## Philosophy

The API should be:

RESTful

Predictable

Versioned

Stateless

Secure

---

## Base URL

```text
/api/v1/
```

Future versions

```text
/api/v2/
```

Never introduce breaking changes without versioning.

---

# Resource Structure

```text
/auth

/users

/social-accounts

/videos

/comments

/analyses

/insights

/recommendations

/settings
```

---

# HTTP Methods

GET

Read data

POST

Create resources

PATCH

Partial update

DELETE

Remove resources

Never use POST for retrieval.

---

# Response Format

Successful

```json
{
  "success": true,
  "data": {},
  "message": null
}
```

Error

```json
{
  "success": false,
  "error": {
    "code": "VIDEO_NOT_FOUND",
    "message": "Video does not exist."
  }
}
```

---

# Status Codes

200 OK

201 Created

204 No Content

400 Bad Request

401 Unauthorized

403 Forbidden

404 Not Found

409 Conflict

422 Validation Error

429 Rate Limited

500 Internal Server Error

---

# Authentication

JWT Bearer Token

Every protected request requires:

Authorization

Bearer TOKEN

---

# Authorization

Every endpoint verifies:

JWT

↓

User

↓

Resource Ownership

↓

Business Rules

Only then execute the request.

---

# Pagination

Large datasets must paginate.

Example

```text
GET /videos?page=1&limit=20
```

Never return thousands of records in one response.

---

# Filtering

Support:

Search

Sort

Date Range

Status

Future:

Topic

Sentiment

Audience Segment

---

# Idempotency

Refreshing analysis multiple times should not create duplicate active records.

Duplicate requests should be safely handled.

---

# Rate Limiting

Future Defaults

Anonymous

50 requests/hour

Authenticated

300 requests/hour

Premium

Unlimited analysis quota (subject to platform limits)

---

# API Documentation

Every endpoint must include:

Purpose

Authentication

Request schema

Response schema

Possible errors

Example request

Example response

This documentation should be generated automatically from FastAPI's OpenAPI specification and remain synchronized with the implementation.

# SYSTEM_DESIGN.md (Part 3)

# 14. Infrastructure

## Philosophy

Infrastructure should remain as simple as possible while supporting future growth.

For the MVP:

* Minimize operational complexity.
* Reduce infrastructure costs.
* Avoid introducing technologies that solve problems the product does not yet have.
* Build for maintainability rather than maximum scale.

Only add new infrastructure when existing architecture becomes a measurable bottleneck.

---

# MVP Infrastructure

```text
                    Users
                      │
                      ▼
          +----------------------+
          |     Next.js App      |
          |    (Frontend)        |
          +----------+-----------+
                     │
               HTTPS Requests
                     │
                     ▼
          +----------------------+
          |      FastAPI API     |
          |    (Backend)         |
          +----------+-----------+
                     │
          +----------+----------+
          |                     |
          ▼                     ▼
   PostgreSQL           AI Provider APIs
      (Neon)             (OpenAI, etc.)
```

---

## Components

### Frontend

Technology

* Next.js
* TypeScript
* Tailwind CSS
* shadcn/ui

Responsibilities

* Authentication UI
* Dashboard
* Charts
* Routing
* State management

Deployment

* Vercel

---

### Backend

Technology

* FastAPI
* SQLAlchemy
* Alembic

Responsibilities

* OAuth
* Business logic
* AI orchestration
* API

Deployment

* Railway / Render / Fly.io

---

### Database

Technology

* PostgreSQL (Neon)

Responsibilities

* Persistent storage
* Transactions
* Relationships
* Analysis history

---

### AI Layer

External services.

Examples

* OpenAI
* Gemini
* Anthropic

The backend abstracts the AI provider so models can be swapped without affecting frontend code.


# Deployment Strategy

## MVP

Single deployment per service.

* One frontend
* One backend
* One PostgreSQL database

---

## Scaling Strategy

Scale independently.

Frontend

↓

Backend

↓

Workers

↓

Database

Each service should scale without requiring changes to others.

---

# Environment Variables

Never hardcode secrets.

Required variables include:

```env
DATABASE_URL=

JWT_SECRET=

YOUTUBE_CLIENT_ID=

YOUTUBE_CLIENT_SECRET=

OPENAI_API_KEY=

FRONTEND_URL=

BACKEND_URL=

ENVIRONMENT=
```

---

# Secrets Management

Secrets must never:

* Be committed to Git.
* Be logged.
* Be exposed to the frontend.
* Be stored in client-side code.

Secrets belong exclusively to the backend.

# Service Boundaries

Frontend never:

* Talks directly to PostgreSQL.
* Calls AI providers.
* Verifies JWTs.

Backend never:

* Renders UI.
* Stores presentation logic.

Database never:

* Performs AI analysis.
* Contains business rules.

Each service has a single responsibility.

---

# 15. Cost Optimization Strategy

## Engineering Goal

Reduce recurring costs while maintaining a premium user experience.

Every engineering decision should consider:

* API usage
* Database load
* AI token usage
* Network bandwidth
* Storage requirements

---

# Cost Hierarchy

Most expensive

↓

LLM inference

↓

Embeddings

↓

YouTube API

↓

Database writes

↓

Database reads

↓

Memory

↓

CPU

Least expensive

Optimize from the top down.

---

# AI Optimization

Never analyze comments twice.

Store:

* embeddings
* summaries
* recommendations
* topic clusters

Always reuse stored analyses whenever possible.

---

# YouTube API Optimization

Only fetch:

* Videos during sync.
* Comments during analysis or refresh.

Never request comments simply because a dashboard loads.

---

# Lazy Loading

Fetch data only when needed.

Dashboard

↓

Video list only

↓

User clicks video

↓

Fetch analysis

↓

User requests refresh

↓

Fetch new comments

This minimizes API usage and improves perceived performance.

---

# Database Optimization

Prefer reads over writes.

Batch inserts whenever possible.

Avoid N+1 queries.

Use indexed columns for:

* user_id
* social_account_id
* video_id
* analysis_id
* created_at

---

# AI Request Optimization

Large comment sets should be processed intelligently.

Pipeline

Comments

↓

Clean

↓

Remove duplicates

↓

Remove spam

↓

Cluster

↓

Representative samples

↓

LLM

Never send every comment directly to an LLM.

# Network Optimization

Compress responses.

Paginate large datasets.

Avoid sending unused fields.

Only request data required by the current screen.

---

# 16. Monitoring & Observability

## Philosophy

If something cannot be measured, it cannot be improved.

Every important action should be observable.

---

# Logging

Log:

Authentication

OAuth

Video imports

Comment imports

Analysis requests

AI responses

Failures

Retries

Unexpected exceptions

Never log:

Passwords

OAuth tokens

JWT secrets

API keys

Sensitive personal information

---

# Metrics

Track:

Users registered

Daily active users

Videos imported

Videos analyzed

Comments processed

Average comments per analysis

Average analysis duration

Average AI cost

Average YouTube API usage

Average response time

Error rate

Retry rate

Database query time

---

# Infrastructure Metrics

Backend

* CPU usage
* Memory usage
* Request latency

Database

* Connection count
* Slow queries
* Storage growth

Future Workers

* Queue depth
* Jobs completed
* Failed jobs
* Average processing time

---

# AI Metrics

Every analysis records:

Input tokens

Output tokens

Embedding tokens

Model

Prompt version

Cost

Duration

Confidence score

These metrics help optimize prompts and control expenses.

---

# Error Monitoring

Unexpected exceptions should be reported automatically.

Examples:

* Sentry
* Better Stack
* Logtail

Every error should include:

* User ID
* Endpoint
* Timestamp
* Stack trace
* Request ID

---

# Health Checks

Expose endpoints such as:

```text
GET /health

GET /health/database

GET /health/ai
```

Purpose

* Deployment verification
* Uptime monitoring
* Infrastructure automation

---

# Performance Monitoring

Measure:

API latency

Database latency

AI latency

Total request duration

Identify bottlenecks before users notice them.

---

# Audit Logs

Critical actions should be auditable.

Examples

User login

YouTube connection

Analysis started

Analysis completed

Account deleted

Settings changed

Audit logs should be immutable.

---

# Dashboards

Internal dashboard should display:

* Daily analyses
* AI cost
* API usage
* Failure rate
* Queue size
* Active users
* Storage growth

---

# 17. Security Architecture

## Philosophy

Security is built into every layer.

Never rely on frontend validation.

Every request is considered untrusted until verified.

---

# Authentication Flow

```text
User

↓

OAuth (Google)

↓

Backend

↓

Create or Find User

↓

Generate JWT

↓

Return Token

↓

Authenticated Requests
```

---

# Authorization Flow

Every request follows:

JWT

↓

Extract User

↓

Locate Resource

↓

Verify Ownership

↓

Execute Request

Never query data before verifying ownership.

---

# Security Layers

Layer 1

HTTPS only.

Layer 2

JWT Authentication.

Layer 3

Ownership verification.

Layer 4

Input validation.

Layer 5

Database constraints.

Layer 6

Rate limiting.

Defense should exist in multiple layers.

# JWT

Requirements

* Signed
* Expiring
* HttpOnly cookies (preferred) or secure bearer tokens
* Rotatable secrets

Tokens should have reasonable expiration times.

---

# Input Validation

Every request validates:

Types

Length

Required fields

Formats

Never trust:

IDs

Emails

URLs

Strings

Validation occurs before business logic.

# SQL Injection

Always use ORM queries.

Never construct SQL using string interpolation.

Parameterized queries only.

# XSS Protection

Escape user-generated content before rendering.

Sanitize any rich text.

Never render raw HTML from comments.

# Rate Limiting

Protect:

Authentication endpoints

OAuth callbacks

Analysis endpoints

Future public APIs

Respond with HTTP 429 when limits are exceeded.

---

# Sensitive Data

Never expose:

OAuth refresh tokens

Access tokens

JWT secrets

API keys

Internal IDs

Stack traces

Secrets remain exclusively on the server.

---

# Database Security

Use least-privilege database credentials.

Enable encrypted connections.

Perform regular backups.

Restrict public access.

---

# API Security Checklist

Every endpoint must:

* Authenticate user.
* Verify ownership.
* Validate input.
* Return standardized responses.
* Avoid exposing implementation details.
* Log failures securely.

---

# Future Security Enhancements

As OluOra grows, implement:

* Refresh tokens
* Device management
* Session revocation
* Two-factor authentication
* Audit dashboard
* Security alerts
* Suspicious login detection
* Secret rotation
* Key management service
* Web Application Firewall (WAF)

Security should evolve alongside the product while maintaining the principle that user trust is a core feature of the platform.

# SYSTEM_DESIGN.md (Part 4)

# 18. Failure Recovery

## Philosophy

Failure is inevitable.

The system must be designed to:

* Fail gracefully
* Recover automatically whenever possible
* Preserve user data
* Prevent duplicate processing
* Provide meaningful feedback to users

Users should never lose work because an internal service failed.

---

# Types of Failures

The system recognizes several categories of failures.

## External API Failures

Examples

* YouTube API unavailable
* AI provider unavailable
* OAuth provider unavailable
* Network timeout
* Rate limiting

Recovery

* Retry with exponential backoff
* Log failure
* Notify user if retries fail
* Allow manual retry

---

## Database Failures

Examples

* Lost connection
* Transaction timeout
* Deadlock
* Database restart

Recovery

* Retry safe transactions
* Roll back failed transactions
* Never leave partial writes

---

## AI Failures

Examples

* Token limit exceeded
* Invalid response
* Model unavailable
* Timeout

Recovery

* Retry if transient
* Preserve imported comments
* Mark analysis as failed
* Allow user to retry later

---

## User Errors

Examples

* Invalid request
* Unauthorized access
* Deleted YouTube video
* Disconnected account

Recovery

Return clear error messages.

Never retry automatically.

---

# Failure Classification

| Failure             | Retry? | User Action Required |
| ------------------- | ------ | -------------------- |
| Network timeout     | Yes    | No                   |
| AI timeout          | Yes    | No                   |
| YouTube rate limit  | Yes    | No                   |
| Invalid OAuth token | No     | Reconnect account    |
| Deleted video       | No     | Remove video         |
| Invalid request     | No     | Fix request          |
| Database deadlock   | Yes    | No                   |
| Validation error    | No     | Correct input        |

---

# Retry Strategy

```text
Attempt 1

↓

5 seconds

↓

Attempt 2

↓

30 seconds

↓

Attempt 3

↓

2 minutes

↓

Attempt 4

↓

10 minutes

↓

Permanent Failure
```

Retries should stop after a configurable limit.

---

# Transaction Safety

Every write operation must be atomic.

Never allow:

User

↓

Video

↓

Comments

↓

Analysis

↓

Failure halfway through

Use database transactions.

If one step fails:

Rollback everything.

---

# Partial Success

Some operations can partially succeed.

Example

Video imported

↓

Comments imported

↓

AI failed

In this case:

* Keep imported comments.
* Mark analysis as failed.
* Allow retry without downloading comments again.

---

# Idempotency

Every expensive operation must be idempotent.

Example

User accidentally clicks:

Analyze

Five times.

Result

Only one active analysis should be created.

Subsequent requests should reuse the existing job or analysis.

---

# Circuit Breaker (Future)

If an external dependency repeatedly fails:

```text
Normal

↓

Multiple Failures

↓

Circuit Opens

↓

Requests Blocked

↓

Cooldown

↓

Health Check

↓

Circuit Closes
```

This prevents overwhelming failing services.

---

# User Notifications

When failures occur, communicate clearly.

Instead of:

"Something went wrong."

Use:

"Analysis couldn't be completed because the AI service is temporarily unavailable. Please try again in a few minutes."

Messages should always explain:

* What failed
* Why (when possible)
* What the user can do next

---

# Logging Failures

Every failure records:

* Timestamp
* Request ID
* User ID
* Video ID
* Error Type
* Stack Trace
* Retry Count

Never log secrets.

---

# 19. Scaling Strategy

## Philosophy

Scale only when necessary.

Premature optimization increases complexity and maintenance costs.

The architecture should evolve in response to measurable usage.

---

# Scaling Roadmap

## Stage 1 (MVP)

Expected Users

0–500 creators

Architecture

```text
Frontend

↓

Backend

↓

PostgreSQL

↓

AI Provider
```

Characteristics

* Simple
* Low cost
* Easy deployment

---

## Stage 2

Expected Users

500–5,000 creators

Changes

* Redis cache
* Background workers
* Job queue
* Improved monitoring

Architecture

```text
Frontend

↓

Backend

↓

Redis

↓

Workers

↓

PostgreSQL
```

---

## Stage 3

Expected Users

5,000–50,000 creators

Changes

* Multiple API instances
* Load balancer
* Object storage
* CDN
* Horizontal worker scaling

---

## Stage 4

Expected Users

50,000+

Changes

* Distributed job processing
* Vector database
* Search service
* Read replicas
* Multi-region deployment

---

# Horizontal Scaling

Every backend instance should be stateless.

Never store:

* Sessions
* Queues
* Temporary state

inside application memory.

Stateless services can scale horizontally without code changes.

---

# Database Scaling

Initial

Single PostgreSQL instance

↓

Read replicas

↓

Partitioning

↓

Sharding (only if absolutely necessary)

Avoid sharding unless a real bottleneck exists.

---

# AI Scaling

As demand grows:

Instead of

One analysis

↓

One AI request

Move toward

Many analyses

↓

Batch processing

↓

Shared embedding generation

↓

Queue workers

This significantly reduces AI costs.

# API Scaling

Support:

Pagination

Filtering

Compression

Caching

Batch endpoints

Avoid endpoints returning excessive data.

---

# 20. Disaster Recovery

## Philosophy

No system is immune to catastrophic failure.

Recovery planning is part of system design.

---

# Recovery Goals

Objective

Restore service quickly.

Preserve user data.

Minimize downtime.

---

# Recovery Priorities

1. Database
2. User Accounts
3. Analyses
4. Comments
5. Video Metadata
6. Logs

---

# Backup Strategy

Database

Daily full backup

Hourly incremental backup

Retention

30 days

Future

Cross-region replication

---

# Restore Procedure

If database fails:

Deploy new instance

↓

Restore latest backup

↓

Replay incremental backups

↓

Verify integrity

↓

Resume service

---

# Infrastructure Recovery

Infrastructure should be reproducible.

Never rely on manual server configuration.

Deployments should be automated.

Future recommendation

Infrastructure as Code.

Examples

* Terraform
* Pulumi

---

# Secrets Recovery

Secrets should exist outside deployments.

Examples

Cloud Secret Managers

Environment Variables

Password Managers

Never store secrets inside repositories.

---

# AI Provider Failure

If provider becomes unavailable:

Fallback options

Primary Model

↓

Secondary Model

↓

Graceful degradation

↓

Notify user

Analysis quality may vary, but service should continue whenever possible.

---

# Data Integrity Checks

Regularly verify:

* Foreign keys
* Missing analyses
* Orphaned comments
* Duplicate records
* Invalid ownership

Automated maintenance jobs should report inconsistencies.

# Recommendation Engine

Current

LLM-generated recommendations.

Future

Hybrid recommendation engine using:

* AI
* Historical performance
* Audience behavior
* Creator goals

Recommendations should become increasingly personalized.

---

# Semantic Search

Allow creators to search comments using natural language.

Example

"Show me everyone asking about pricing."

"Find comments requesting tutorials."

Implement using embeddings and vector search.

# Export System

Allow exporting:

* PDF reports
* CSV data
* PowerPoint summaries
* AI-generated briefs

Exports should use asynchronous background jobs.

---

# Notifications

Support:

* Email
* In-app
* Push (future)

Examples

* Analysis complete
* Weekly insights
* Trending audience topics
* New recommendations

# Product Vision

OluOra should evolve from:

A comment analysis tool

↓

An audience intelligence platform

↓

A creator decision engine

↓

The operating system for understanding online audiences.

Every architectural decision made today should support that long-term vision while keeping the MVP simple, maintainable, and cost-effective.

---

# Guiding Principles

Every future feature should satisfy the following questions before implementation:

* Does it solve a real user problem?
* Can it be implemented without unnecessary complexity?
* Does it respect user privacy and data ownership?
* Is it cost-effective to operate?
* Can it scale with the existing architecture?
* Does it improve creator decision-making?

If the answer to any of these questions is "no," the feature should be reconsidered before development.

---

# Conclusion

OluOra is designed with a pragmatic architecture that prioritizes simplicity, reliability, and scalability.

The MVP intentionally avoids unnecessary infrastructure while establishing clear architectural boundaries that support future growth. As usage increases, the system can evolve through incremental enhancements—such as background workers, caching, vector search, and distributed processing—without requiring major redesigns.

The principles defined in this document should remain constant regardless of technology changes:

* Keep services loosely coupled.
* Make expensive work reusable.
* Protect user data.
* Build observable systems.
* Prefer simplicity over premature optimization.
* Scale based on evidence, not assumptions.

Following these principles will enable OluOra to grow from an MVP into a robust audience intelligence platform without accumulating unnecessary technical debt.
