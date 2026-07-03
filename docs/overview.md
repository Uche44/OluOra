# OluNdi — Product Requirements & Project Overview

# 1. Executive Summary

**OluNdi** is an AI-powered audience intelligence platform that helps creators understand what their audience truly wants by analyzing conversations across their content.

Every day, creators receive hundreds or thousands of comments. Hidden inside those comments are valuable insights:

* questions viewers repeatedly ask
* pain points they experience
* misconceptions about products or services
* buying intent
* feature requests
* future content ideas

Unfortunately, these signals are buried inside large volumes of unstructured text, making them nearly impossible to analyze manually.

OluNdi transforms these conversations into actionable intelligence.

Instead of reading 5,000 comments, creators instantly understand:

* what people are asking
* why they are asking it
* what content should be created next
* which topics are gaining momentum
* what opportunities they are currently missing

OluNdi is not another analytics dashboard.

It is an AI system that listens to an audience at scale and tells creators exactly what matters.

---

# 2. Vision

Our vision is to become the world's leading **Audience Intelligence Platform** for creators.

Traditional creator analytics answer questions like:

* How many views did I receive?
* How many subscribers did I gain?
* What is my engagement rate?

OluNdi answers entirely different questions:

* What does my audience actually want?
* What is confusing them?
* What content are they requesting?
* What products are they interested in?
* What should I create next?
* How has my audience changed over time?

Our goal is to make audience understanding as measurable and accessible as traditional social media analytics.

In the long term, OluNdi will become the intelligence layer that sits between creators and their audiences, helping creators make every content decision based on evidence rather than assumptions.

---

# 3. Mission

To eliminate guesswork from content creation by turning millions of audience conversations into clear, actionable insights.

Every creator deserves to know exactly what their audience is thinking.

---

# 4. The Problem

Creators spend enormous amounts of time trying to understand their audience.

After publishing a successful video, thousands of comments may arrive within hours.

Inside those comments are answers to important questions:

* Which part of the video confused viewers?
* Which feature generated the most excitement?
* What objections prevented someone from buying?
* What tutorial do viewers want next?
* Which audience segment is growing?

Unfortunately, discovering these answers requires manually reading comments one by one.

As creators grow, this quickly becomes impossible.

Existing analytics platforms focus primarily on numerical metrics such as:

* impressions
* engagement
* watch time
* follower growth
* click-through rate

While useful, these metrics explain **what happened**, not **why it happened**.

Audience conversations contain the missing context.

OluNdi exists to uncover it.

---

# 5. Solution

OluNdi connects directly to a creator's social media accounts and continuously analyzes audience conversations.

Using artificial intelligence, natural language processing, clustering algorithms, and semantic analysis, the platform converts raw comments into structured audience intelligence.

Instead of presenting thousands of comments, OluNdi delivers concise insights such as:

> 38% of viewers are asking about pricing.

> 24% are requesting a beginner tutorial.

> 17% are confused about setup.

> Buying intent increased significantly after your latest video.

The platform doesn't stop at identifying problems.

It recommends what creators should do next.

Examples include:

* Create a pricing breakdown video.
* Record a beginner guide.
* Publish a comparison video.
* Address the most common misconceptions.
* Create FAQ content based on recurring questions.

The objective is to help creators make smarter decisions with confidence.

---

# 6. Product Positioning

OluNdi is **not** a social media analytics platform.

OluNdi is an **Audience Intelligence Platform.**

Traditional analytics platforms measure performance.

OluNdi measures audience understanding.

Instead of focusing on metrics like:

* views
* likes
* impressions
* followers

OluNdi focuses on:

* audience intent
* recurring questions
* buying signals
* audience sentiment
* content demand
* emerging trends

This positioning differentiates OluNdi from conventional creator dashboards.

---

# 7. Target Users

## Primary Users

Creators who publish educational or informative content, including:

* YouTubers
* TikTok creators
* online educators
* SaaS founders
* coaches
* consultants
* product reviewers
* technical creators
* finance creators
* developers
* AI creators

These creators rely heavily on audience engagement and frequently receive large volumes of comments.

---

## Secondary Users

Future expansion includes:

* creator agencies
* influencer marketing agencies
* digital marketing teams
* brands
* product managers
* customer success teams
* research organizations

---

# 8. Core Value Proposition

OluNdi enables creators to answer questions they currently cannot answer efficiently.

Instead of wondering:

"What video should I make next?"

They know.

Instead of asking:

"What are people confused about?"

They know.

Instead of reading comments for three hours every evening...

They receive an AI-generated summary within minutes.

---

# 9. MVP Features

## 9.1 Social Authentication

Creators authenticate using their existing creator accounts.

Supported platforms:

* YouTube
* TikTok

Authentication also authorizes OluNdi to retrieve creator-owned content and associated comments.

---

## 9.2 Creator Dashboard

After login, creators land on a dashboard displaying their connected content.

Each video displays:

* thumbnail
* title
* publish date
* views
* likes
* comments
* engagement summary
* analysis status

Videos are intentionally loaded first without comments to minimize latency.

Comment retrieval begins only when analysis is requested.

---

## 9.3 Video Analysis

Selecting a video initiates an analysis pipeline.

The system retrieves comments directly from the platform API.

Comment retrieval is performed on demand to reduce unnecessary API calls and improve scalability.

---

## 9.4 AI Processing Pipeline

Each analysis follows a structured pipeline.

1. Retrieve comments
2. Clean and normalize text
3. Detect language
4. Remove spam and duplicates
5. Extract frequently asked questions
6. Generate semantic embeddings
7. Cluster similar discussions
8. Identify recurring themes
9. Measure topic prevalence
10. Generate actionable insights
11. Produce content recommendations

---

## 9.5 Audience Intelligence

The final analysis presents structured insights including:

### Topic Distribution

Example:

* Pricing Questions — 38%
* Beginner Tutorials — 24%
* Feature Requests — 15%
* Technical Issues — 11%
* General Feedback — 12%

---

### Most Asked Questions

Examples:

* Is this free?
* Can beginners use this?
* How does pricing work?
* Does this work on mobile?
* Which plan should I choose?

---

### Audience Pain Points

Examples:

* Setup confusion
* Missing documentation
* Feature discoverability
* Pricing uncertainty

---

### Positive Feedback

Examples:

* Easy to understand
* Helpful explanation
* Saved me time

---

### Content Opportunities

Examples:

* Beginner tutorial
* Pricing breakdown
* Product comparison
* Frequently asked questions
* Common mistakes

---

# 10. Technical Architecture

## Frontend

Technology:

* Next.js
* TypeScript
* Tailwind CSS
* TanStack Query
* Zustand
* shadcn/ui

Responsibilities:

* authentication
* dashboard
* video management
* insight visualization
* user settings

---

## Backend

Technology:

* FastAPI
* SQLAlchemy
* Alembic
* PostgreSQL
* JWT Authentication

Responsibilities:

* OAuth authentication
* video retrieval
* comment retrieval
* AI orchestration
* data persistence
* API responses

---

## AI Layer

Responsibilities:

* comment preprocessing
* semantic embeddings
* clustering
* insight generation
* recommendation engine

Future versions may incorporate retrieval-augmented generation, vector databases, and custom fine-tuned models as the platform scales.

---

## Database

Core entities include:

* Users
* Social Accounts
* Videos
* Comments
* Analyses
* Insights
* Questions

The schema is designed to support multiple social platforms while maintaining a unified audience intelligence model.

---

# 11. Product Workflow

The complete creator journey is designed to be simple.

1. Creator signs in with YouTube or TikTok.
2. OluNdi imports the creator's videos.
3. Dashboard displays available videos.
4. Creator selects a video.
5. OluNdi retrieves comments.
6. AI analyzes audience conversations.
7. Insights are generated.
8. Creator receives actionable recommendations.
9. Creator creates better content based on real audience demand.

---

# 12. Long-Term Roadmap

The MVP focuses on individual video analysis.

Future releases will expand OluNdi into a comprehensive creator intelligence platform.

Planned capabilities include:

### Cross-Platform Intelligence

Support for:

* Instagram
* X
* Reddit
* LinkedIn
* Facebook
* Threads

---

### Audience Memory

Rather than analyzing one video at a time, OluNdi will understand audience evolution across months or years of content.

Creators will see how interests, questions, and trends change over time.

---

### AI Content Planner

Automatically generate:

* weekly content calendars
* publishing schedules
* topic prioritization
* content series
* thumbnail suggestions
* title recommendations

---

### Audience Segmentation

Identify:

* beginners
* advanced users
* buyers
* casual viewers
* loyal followers

Each segment will receive its own insight profile.

---

### Brand Intelligence

Brands will be able to analyze creator audiences before launching partnerships.

---

### Competitive Intelligence

Creators can compare audience interests against competitors to identify content gaps and emerging opportunities.

---

# 13. Monetization Strategy

## Free Plan

* limited analyses
* basic audience insights
* limited history

---

## Creator Pro

* unlimited analyses
* advanced audience intelligence
* AI recommendations
* historical trends
* exports

---

## Team & Agency

* multiple creator workspaces
* collaborative dashboards
* client reporting
* white-label exports
* centralized analytics

---

# 14. Competitive Advantage

Most analytics platforms answer:

"What happened?"

OluNdi answers:

"Why did it happen, and what should you do next?"

This distinction creates a defensible position in the creator economy.

Rather than competing on metrics already offered by established platforms, OluNdi focuses on interpreting audience conversations and converting them into strategic decisions.

Its long-term advantage lies in building a proprietary understanding of audience behavior that becomes more valuable as more conversations are analyzed.

---

# 15. Success Metrics

Product success will be measured by:

* creators onboarded
* connected social accounts
* videos analyzed
* comments processed
* insights generated
* repeat analyses
* weekly active creators
* creator retention
* recommendation adoption rate
* time saved compared to manual analysis

These metrics reflect not only platform usage but also the value OluNdi delivers to creators.

---

# 16. Long-Term Opportunity

Audience conversations are one of the richest and least-utilized datasets in the creator economy.

Every comment represents a signal—an opinion, a question, a request, or an unmet need.

OluNdi's long-term ambition is to become the system that continuously interprets those signals and helps creators act on them.

As the platform expands across social networks and accumulates historical audience data, it will evolve from a comment analysis tool into the central intelligence platform creators rely on to understand their communities, shape their content strategies, strengthen audience relationships, and grow sustainable businesses.
