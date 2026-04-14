# OluNdi — Project Documentation

## 1. Product Overview

**OluNdi** is an AI-powered creator analytics platform that analyzes comments from social media videos and extracts meaningful insights about audience interests, questions, and feedback.

Content creators often receive **hundreds or thousands of comments** on their videos. Within those comments are valuable signals about:

* what viewers are confused about
* what viewers want to learn next
* what product questions people have
* what content resonates most with the audience

However, manually reading thousands of comments is **impractical and time-consuming**.

OluNdi solves this problem by automatically analyzing comment data from creator videos and converting it into **structured audience intelligence**.

Instead of scrolling through comments, creators receive insights like:

* “38% of viewers are asking about pricing.”
* “21% want a beginner tutorial.”
* “15% are confused about setup.”

These insights allow creators to:

* understand their audience faster
* produce content people are actively requesting
* increase engagement and retention
* identify opportunities for monetization

The platform initially focuses on creators publishing content on **video-based platforms** such as:

* YouTube
* TikTok

---

# 2. Vision

The long-term vision of OluNdi is to become **the intelligence layer for creator audiences**.

Instead of creators guessing what content to produce next, OluNdi will provide **data-driven content insights derived directly from audience conversations**.

In the future, the platform can expand to support:

* brand sentiment analysis
* product feedback mining
* creator audience research
* automated content strategy recommendations

---

# 3. Problem Statement

Creators struggle with extracting useful insights from audience interactions.

### Key challenges

1. **Comment overload**

Popular videos can generate thousands of comments. Important insights get buried inside large volumes of text.

2. **Manual analysis is impossible**

Reading comments one by one takes too much time.

3. **Creators miss content opportunities**

Many creators ask:

* “What video should I make next?”
* “What questions do people have?”
* “What part of my video confused viewers?”

These answers already exist inside the comments but are difficult to identify.

4. **Existing analytics tools focus on metrics**

Most analytics platforms provide metrics like:

* views
* watch time
* follower growth

But they **do not analyze audience conversations**.

---

# 4. Solution

OluNdi uses AI and natural language processing to analyze comments and extract meaningful patterns.

The platform processes comment data to:

1. Identify **frequently asked questions**
2. Detect **recurring audience topics**
3. Cluster comments by theme
4. Generate **actionable insights**
5. Suggest new content ideas

Example insight output:

```
38% of viewers are asking about pricing
22% want a beginner tutorial
14% are confused about setup
```

The system also generates content ideas such as:

* “Create a video explaining your pricing model”
* “Make a beginner guide”
* “Record a detailed setup tutorial”

---

# 5. Target Users

## Primary Users

**Content creators**

Examples:

* YouTubers
* TikTok creators
* educational creators
* product reviewers
* SaaS founders making content
* online educators

### Creator Pain Points

Creators want to know:

* what their audience wants
* what questions viewers are asking
* which topics they should cover next

---

## Secondary Users (future expansion)

* influencer marketing agencies
* brands analyzing influencer audiences
* product teams analyzing user feedback

---

# 6. Core Features (MVP)

## 1. Creator Authentication

Creators sign up using their social media accounts.

Authentication options:

* YouTube login
* TikTok login

After authentication, the platform can access the creator’s videos.

---

## 2. Creator Dashboard

The dashboard displays all videos belonging to the creator.

Each video card includes:

* video thumbnail
* title
* view count
* like count
* comment count
* analyze button

Users can select a video to analyze its comments.

---

## 3. Comment Fetching

When a video is selected, the system fetches comments using platform APIs.

For example:

YouTube comments can be retrieved using the official API from Google.

Comment data includes:

* comment text
* like count
* author
* timestamp

---

## 4. Comment Processing

After comments are retrieved, the system processes them through an AI pipeline.

Steps include:

1. Text cleaning
2. Language normalization
3. Embedding generation
4. Topic clustering
5. Insight extraction

---

## 5. Audience Insight Generation

After clustering comment topics, the platform generates insight summaries such as:

```
38% asking about pricing
27% asking how the tool works
18% requesting tutorials
```

Insights are displayed visually using charts and cards.

---

## 6. Trending Questions

The system extracts the most frequently asked questions.

Example output:

* “Is this free?”
* “Can beginners use this?”
* “Where can I buy this?”

---

## 7. Content Idea Generator

Based on detected audience questions, OluNdi suggests content ideas.

Examples:

Suggested content:

* “Complete beginner tutorial”
* “How pricing works”
* “Common mistakes beginners make”

---

# 7. Technical Architecture

The platform uses a modern web architecture composed of three main layers.

### Frontend

The user interface is built using:

* Next.js

The frontend provides:

* authentication UI
* dashboard
* video insights pages
* charts and analytics visualization

---

### Backend

The backend API is built using:

* FastAPI

Responsibilities include:

* user authentication
* video retrieval
* comment retrieval
* analysis pipeline
* API responses

---

### Database

All application data is stored in:

* PostgreSQL

Tables include:

* users
* videos
* comments
* analysis results

---

# 8. AI Analysis Pipeline

The AI pipeline converts raw comments into insights.

Steps:

1. Fetch comments
2. Clean and preprocess text
3. Generate embeddings
4. Cluster similar comments
5. Extract recurring topics
6. Calculate frequency percentages
7. Generate insights

This transforms thousands of comments into a **structured audience understanding**.

---

# 9. Example Insight Output

Example video with 2,000 comments.

OluNdi analysis:

```
Topic Breakdown

Pricing questions — 38%
Beginner questions — 27%
Feature requests — 15%
General feedback — 12%
Other — 8%
```

Suggested content ideas:

* Pricing breakdown video
* Beginner tutorial
* Feature comparison video

---

# 10. Monetization Strategy

Possible pricing model:

### Free Tier

* limited analyses
* basic insights

### Pro Plan

* unlimited video analysis
* deeper audience insights
* content idea generation

### Agency Plan (future)

* multi-creator dashboards
* white-label reports

---

# 11. Competitive Advantage

Most social media analytics platforms focus on:

* follower growth
* impressions
* engagement metrics

Platforms like:

* Socialinsider
* Agorapulse
* HypeAuditor

do not deeply analyze **comment conversations**.

OluNdi focuses on **audience voice extraction**, which is a less crowded niche.

---

# 12. Future Roadmap

Potential future features include:

### Multi-platform support

Additional platforms:

* Instagram
* X (Twitter)
* Reddit
* LinkedIn

---

### AI Content Planner

Automatically generate:

* weekly content calendars
* video topic suggestions

---

### Sentiment Analysis

Detect:

* positive feedback
* negative feedback
* audience sentiment trends

---

### Brand Insights

Brands could analyze:

* influencer audiences
* product feedback in comments

---

# 13. Success Metrics

Key metrics for product success:

* number of creators onboarded
* number of videos analyzed
* insights generated per user
* creator retention rate

---

# 14. Long-Term Opportunity

Audience conversations are one of the most underutilized data sources in social media.

OluNdi positions itself as a platform that **transforms unstructured audience conversations into strategic insights for creators and brands**.

If executed well, the platform can evolve into a **creator intelligence platform used by thousands of creators globally**.

---
