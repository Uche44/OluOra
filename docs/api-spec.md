# API_SPEC.md

# OluOra API Specification

Version: 1.0 (MVP)

---

# Purpose

This document defines the REST API contract for the OluOra backend.

It serves as the single source of truth for:

* Frontend developers
* Backend developers
* AI coding agents
* API documentation
* Future mobile applications

All endpoints should follow the standards defined in this document.

# API Principles

The API must be:

* RESTful
* Stateless
* Predictable
* Secure
* Versioned
* Consistent

---

# Base URL

```text
/api/v1
```

Future versions

```text
/api/v2
```

---

# Authentication

The MVP uses **Google OAuth (YouTube)**.

Authentication Flow

```text
Frontend
      │
      ▼
Google OAuth
      │
      ▼
Backend Callback
      │
      ▼
Create / Find User
      │
      ▼
Generate JWT
      │
      ▼
Return Access Token
```

Every protected endpoint requires:

```http
Authorization: Bearer <JWT_TOKEN>
```

---

# Standard Response Format

## Success

```json
{
    "success": true,
    "message": "Success",
    "data": {}
}
```

---

## Error

```json
{
    "success": false,
    "error": {
        "code": "VIDEO_NOT_FOUND",
        "message": "The requested video does not exist."
    }
}
```

---

# HTTP Status Codes

| Code | Meaning               |
| ---- | --------------------- |
| 200  | Success               |
| 201  | Created               |
| 204  | No Content            |
| 400  | Bad Request           |
| 401  | Unauthorized          |
| 403  | Forbidden             |
| 404  | Not Found             |
| 409  | Conflict              |
| 422  | Validation Error      |
| 429  | Rate Limited          |
| 500  | Internal Server Error |

---

# Authentication Endpoints

## Login with Google

```http
GET /auth/google/login
```

Redirects user to Google OAuth.

Authentication

❌ No

---

## Google Callback

```http
GET /auth/google/callback
```

Creates or logs in the user.

Returns

```json
{
    "access_token": "...",
    "token_type": "Bearer",
    "user": {}
}
```

Authentication

❌ No

---

## Get Current User

```http
GET /auth/me
```

Returns the currently authenticated user.

Authentication

✅ Required

---

## Logout

```http
POST /auth/logout
```

Invalidates session (future).

Authentication

✅ Required

---

# User Endpoints

## Get Profile

```http
GET /users/me
```

Returns:

* id
* name
* email
* avatar
* connected accounts

---

## Update Preferences

```http
PATCH /users/preferences
```

Allows updating:

* notifications
* analysis settings
* theme (future)

---

## Delete Account

```http
DELETE /users/me
```

Deletes:

* account
* videos
* analyses
* comments

---

# YouTube Endpoints

## Connect YouTube

```http
GET /youtube/connect
```

Starts OAuth process.

---

## Disconnect Account

```http
DELETE /youtube/disconnect
```

Removes connected account.

Does not delete analyses unless requested.

---

## Sync Videos

```http
POST /youtube/sync
```

Imports latest YouTube videos.

Returns

```json
{
    "videos_imported": 25
}
```

---

# Video Endpoints

## Get Videos

```http
GET /videos
```

Supports

* pagination
* search
* sorting

Query Parameters

```text
?page=1

?limit=20

?search=tutorial

?sort=published_at
```

Returns

```json
{
    "videos": [],
    "pagination": {}
}
```

---

## Get Single Video

```http
GET /videos/{video_id}
```

Returns

* metadata
* statistics
* analysis status

---

## Refresh Video Metadata

```http
POST /videos/{video_id}/refresh
```

Refreshes:

* views
* likes
* comments count

Does **not** analyze comments.

---

# Analysis Endpoints

## Analyze Video

```http
POST /videos/{video_id}/analyze
```

Pipeline

```text
Fetch Comments

↓

Clean Comments

↓

Generate Embeddings

↓

Cluster Topics

↓

Generate Insights

↓

Save Analysis
```

Returns

```json
{
    "analysis_id": "...",
    "status": "completed"
}
```

---

## Refresh Analysis

```http
POST /analyses/{analysis_id}/refresh
```

Creates a new analysis version.

Does not overwrite previous analysis.

---

## Get Analysis

```http
GET /analyses/{analysis_id}
```

Returns

* summary
* insights
* recommendations
* questions
* charts

---

## Delete Analysis

```http
DELETE /analyses/{analysis_id}
```

Removes analysis only.

Comments remain.

---

# Insight Endpoints

## Get Insights

```http
GET /analyses/{analysis_id}/insights
```

Returns

Example

```json
[
    {
        "topic":"Pricing",
        "percentage":38
    }
]
```

---

## Get Summary

```http
GET /analyses/{analysis_id}/summary
```

Returns

```json
{
    "summary":"Most viewers are asking about pricing."
}
```

---

# Question Endpoints

## Get Frequently Asked Questions

```http
GET /analyses/{analysis_id}/questions
```

Returns

```json
[
    {
        "question":"Is this free?",
        "mentions":217
    }
]
```

---

# Recommendation Endpoints

## Get Recommendations

```http
GET /analyses/{analysis_id}/recommendations
```

Returns

```json
[
    {
        "title":"Create a Pricing Video",
        "priority":"High"
    }
]
```

---

# Comment Endpoints

## Get Comments

```http
GET /videos/{video_id}/comments
```

Supports

* pagination
* search

Primarily for debugging and transparency.

Not intended to display every comment by default.

---

# Dashboard Endpoints

## Dashboard Overview

```http
GET /dashboard
```

Returns

* total videos
* analyzed videos
* comments analyzed
* top insight
* latest analyses
* recommendations

---

## Dashboard Statistics

```http
GET /dashboard/stats
```

Returns metrics for charts.

---

# Settings Endpoints

## Get Settings

```http
GET /settings
```

---

## Update Settings

```http
PATCH /settings
```

Supports

* notifications
* default analysis behavior
* timezone (future)

---

# Pagination Standard

All collection endpoints use:

```text
?page=1

&limit=20
```

Response

```json
{
    "data": [],
    "pagination": {
        "page":1,
        "limit":20,
        "total":140,
        "pages":7
    }
}
```

---

# Filtering

Supported filters

```text
search

sort

status

date_from

date_to
```

Future

```text
topic

sentiment

language
```

---

# Sorting

Examples

```text
?sort=published_at

?sort=views

?sort=title

?sort=comments
```

---

# Error Codes

Examples

```text
UNAUTHORIZED

FORBIDDEN

VIDEO_NOT_FOUND

ANALYSIS_NOT_FOUND

INVALID_TOKEN

ACCOUNT_NOT_CONNECTED

RATE_LIMIT_EXCEEDED

VALIDATION_ERROR

INTERNAL_SERVER_ERROR
```

---

# Validation Rules

All endpoints validate:

* UUIDs
* Required fields
* Data types
* Payload length
* Query parameters

Reject invalid requests before business logic executes.

---

# Rate Limiting

Future Defaults

Anonymous

* 50 requests/hour

Authenticated

* 300 requests/hour

Premium

* Higher analysis quotas and API limits

---

# Security

Every protected endpoint must:

* Verify JWT
* Verify resource ownership
* Validate request
* Return standardized responses

Never expose:

* OAuth tokens
* Internal secrets
* Stack traces

---

# API Versioning

Breaking changes require a new version.

Example

```text
/api/v1/videos

/api/v2/videos
```

Maintain backward compatibility whenever feasible.

---

# OpenAPI Documentation

FastAPI automatically generates:

* Swagger UI
* OpenAPI Specification
* ReDoc

Development URLs

```text
/docs

/redoc

/openapi.json
```

These should remain enabled in development and disabled or protected appropriately in production.

---

# Future Endpoints

Planned additions

* `/exports`
* `/notifications`
* `/webhooks`
* `/teams`
* `/billing`
* `/api-keys`
* `/usage`
* `/integrations`
* `/search`
* `/trends`

---

# API Design Principles

Every endpoint should adhere to these rules:

* Follow REST conventions.
* Use nouns for resources, not verbs.
* Return consistent response formats.
* Keep endpoints focused on a single responsibility.
* Require authentication where appropriate.
* Validate all inputs.
* Paginate large datasets.
* Never expose internal implementation details.
* Design endpoints to be reusable across web, mobile, and future third-party clients.

The API should be intuitive, predictable, and stable, enabling frontend applications and future integrations to interact with OluOra without needing knowledge of backend implementation details.
