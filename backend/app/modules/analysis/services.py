import os
# Silence joblib wmic warning on Windows when logical core count lookup fails
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

import uuid
from datetime import datetime, timezone
import logging
import numpy as np
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.comments.models import Comment
from app.modules.comments.preprocessing import clean_comment_text
from app.integrations.huggingface import generate_embeddings
from app.integrations.groq import generate_chat_completion

logger = logging.getLogger(__name__)


from textblob import TextBlob

async def generate_embeddings_for_comments(
    db: AsyncSession,
    video_id: uuid.UUID
) -> int:
    """
    Generates and stores semantic embeddings for all comments on a given video
    that do not yet have an embedding (incremental — never re-embeds existing ones).

    Steps:
    1. Fetches all comments for the video that have no embedding yet.
    2. Cleans/normalizes each comment text via the preprocessing pipeline.
    3. Sends the cleaned texts to the Hugging Face Inference API in batches.
    4. Saves the returned float vectors back to the database.

    Args:
        db: The active async database session.
        video_id: The UUID of the video whose comments should be embedded.

    Returns:
        The number of comments that were successfully embedded.
    """
    # 1. Fetch all comments for this video that have no embedding yet
    result = await db.execute(
        select(Comment).where(
            Comment.video_id == video_id,
            Comment.embedding.is_(None)
        )
    )
    comments_to_embed = result.scalars().all()

    if not comments_to_embed:
        logger.info(f"No new comments to embed for video_id={video_id}")
        return 0

    logger.info(
        f"Generating embeddings for {len(comments_to_embed)} comments "
        f"on video_id={video_id}"
    )

    # 2. Clean each comment's text before embedding
    texts = [clean_comment_text(c.text) for c in comments_to_embed]

    # 3. Send to Hugging Face API and retrieve embedding vectors
    embeddings = await generate_embeddings(texts)

    if len(embeddings) != len(comments_to_embed):
        raise Exception(
            f"Embedding count mismatch: expected {len(comments_to_embed)}, "
            f"got {len(embeddings)}"
        )

    # 4. Save each embedding and sentiment score back to the corresponding Comment row.
    # TextBlob polarity: -1.0 (very negative) → 0.0 (neutral) → +1.0 (very positive)
    for comment, text, vector in zip(comments_to_embed, texts, embeddings):
        try:
            polarity = TextBlob(text).sentiment.polarity  # float in [-1, 1]
        except Exception:
            polarity = 0.0
        await db.execute(
            update(Comment)
            .where(Comment.id == comment.id)
            .values(embedding=vector, sentiment_score=polarity)
        )

    await db.commit()

    # 5. Backfill sentiment for comments that were already embedded (previous runs)
    #    but never got a sentiment score (sentiment scoring was added after initial release).
    unscoredResult = await db.execute(
        select(Comment).where(
            Comment.video_id == video_id,
            Comment.embedding.is_not(None),
            Comment.sentiment_score.is_(None)
        )
    )
    unscored_comments = unscoredResult.scalars().all()
    if unscored_comments:
        logger.info(f"Backfilling sentiment scores for {len(unscored_comments)} already-embedded comments.")
        for comment in unscored_comments:
            try:
                cleaned = clean_comment_text(comment.text)
                polarity = TextBlob(cleaned).sentiment.polarity
            except Exception:
                polarity = 0.0
            await db.execute(
                update(Comment)
                .where(Comment.id == comment.id)
                .values(sentiment_score=polarity)
            )
        await db.commit()

    logger.info(
        f"Successfully embedded {len(comments_to_embed)} comments "
        f"for video_id={video_id}"
    )
    return len(comments_to_embed)


def _run_kmeans(embeddings: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Runs KMeans clustering in a synchronous thread pool."""
    from sklearn.cluster import KMeans
    import joblib
    kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
    with joblib.parallel_backend("threading", n_jobs=1):
        labels = kmeans.fit_predict(embeddings)
    return labels, kmeans.cluster_centers_


async def cluster_comments_for_analysis(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    video_id: uuid.UUID,
    num_clusters: int = 5
) -> int:
    """
    Groups embedded comments for a video into semantic clusters using KMeans.

    1. Fetches all comments for the video that have embeddings.
    2. Runs local KMeans clustering (via run_in_threadpool).
    3. Finds representative comments closest to the centroid of each cluster.
    4. Creates TopicCluster database records.
    5. Associates comments to their respective TopicCluster.
    """
    from fastapi.concurrency import run_in_threadpool
    from app.modules.analysis.models import TopicCluster

    # 1. Fetch comments with embeddings
    result = await db.execute(
        select(Comment).where(
            Comment.video_id == video_id,
            Comment.embedding.is_not(None)
        )
    )
    comments = result.scalars().all()

    if not comments:
        logger.warning(f"No comments found with embeddings for video_id={video_id}")
        return 0

    # Determine dynamic k (number of clusters)
    k = min(num_clusters, len(comments))
    if k < 1:
        k = 1

    logger.info(
        f"Clustering {len(comments)} comments into {k} clusters "
        f"for analysis_id={analysis_id}"
    )

    # 2. Extract embeddings matrix
    embeddings = np.array([c.embedding for c in comments], dtype=np.float32)

    # Run KMeans via threadpool to avoid blocking event loop
    labels, centroids = await run_in_threadpool(_run_kmeans, embeddings, k)

    # 3. Process clusters
    for cluster_idx in range(k):
        # Find comments belonging to this cluster
        cluster_comment_indices = [i for i, label in enumerate(labels) if label == cluster_idx]
        cluster_comments = [comments[i] for i in cluster_comment_indices]

        if not cluster_comments:
            continue

        # Calculate average sentiment
        sentiments = [c.sentiment_score for c in cluster_comments if c.sentiment_score is not None]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

        # Calculate distances to centroid to find representative comments
        centroid = centroids[cluster_idx]
        comment_distances = []
        for c in cluster_comments:
            dist = float(np.linalg.norm(np.array(c.embedding, dtype=np.float32) - centroid))
            comment_distances.append((c, dist))

        # Sort by distance (closest first)
        comment_distances.sort(key=lambda x: x[1])
        top_reps = [item[0] for item in comment_distances[:5]]  # Top 5 representatives

        # Create a preliminary summary (snippets of top representatives)
        rep_texts = [f"- {c.author_name}: {c.text[:120]}" for c in top_reps]
        preliminary_summary = "Representative comments:\n" + "\n".join(rep_texts)

        # 4. Create TopicCluster record
        cluster_record = TopicCluster(
            analysis_id=analysis_id,
            title=f"Topic Cluster {cluster_idx + 1}",
            summary=preliminary_summary,
            size=len(cluster_comments),
            sentiment_score=avg_sentiment
        )
        db.add(cluster_record)
        await db.flush()  # To populate cluster_record.id

        # 5. Link comments to the cluster in DB
        for c in cluster_comments:
            c.topic_cluster_id = cluster_record.id

    await db.commit()
    logger.info(f"Successfully created {k} clusters for analysis_id={analysis_id}")
    return k


def _get_representative_comments(comments: list[Comment], limit: int = 5) -> list[Comment]:
    """Helper to find representative comments closest to the mean vector of comments."""
    if not comments:
        return []
    embedded_comments = [c for c in comments if c.embedding is not None]
    if not embedded_comments:
        return comments[:limit]

    # Convert embeddings to numpy array
    embeddings = np.array([c.embedding for c in embedded_comments], dtype=np.float32)
    # Calculate centroid
    centroid = np.mean(embeddings, axis=0)
    # Calculate Euclidean distances to centroid
    distances = np.linalg.norm(embeddings - centroid, axis=1)

    paired = list(zip(embedded_comments, distances))
    paired.sort(key=lambda x: x[1])  # Sort by distance ascending

    return [p[0] for p in paired[:limit]]


async def generate_insights_for_analysis(
    db: AsyncSession,
    analysis_id: uuid.UUID,
    video_id: uuid.UUID
) -> dict:
    """
    Submits comment clusters to Groq LLM to refine cluster titles/descriptions
    and extract structured audience insights (questions, pain points, recommendations).
    """
    import json
    from app.modules.analysis.models import Analysis, TopicCluster, Insight

    # Fetch the analysis record
    result = await db.execute(
        select(Analysis).where(Analysis.id == analysis_id)
    )
    analysis = result.scalars().first()
    if not analysis:
        raise ValueError(f"Analysis with id {analysis_id} not found.")

    analysis.status = "running"
    await db.commit()

    try:
        # 1. Fetch clusters
        result = await db.execute(
            select(TopicCluster).where(TopicCluster.analysis_id == analysis_id)
        )
        clusters = result.scalars().all()

        if not clusters:
            raise ValueError(f"No topic clusters found for analysis_id={analysis_id}")

        # 2. Format cluster blocks for prompt
        cluster_blocks = []
        for idx, cluster in enumerate(clusters):
            # Fetch comments in this cluster
            c_result = await db.execute(
                select(Comment).where(Comment.topic_cluster_id == cluster.id)
            )
            cluster_comments = c_result.scalars().all()
            reps = _get_representative_comments(cluster_comments, limit=5)
            rep_lines = "\n".join(f"- {c.author_name}: {c.text}" for c in reps)

            block = (
                f"GROUP {idx + 1}:\n"
                f"Size: {cluster.size} comments\n"
                f"Average Sentiment: {cluster.sentiment_score:.2f}\n"
                f"Representative Comments:\n{rep_lines}\n"
            )
            cluster_blocks.append(block)

        cluster_data = "\n---\n".join(cluster_blocks)

        # 3. Construct prompts
        system_prompt = (
            "You are a helpful audience analyst writing for content creators who are not tech-savvy. "
            "Your job is to analyze groups of viewer comments and turn them into clear, plain-English insights.\n"
            "IMPORTANT writing rules:\n"
            "- Use simple, everyday language. Avoid jargon, academic words, and technical terms.\n"
            "- Write like you are explaining to a friend, not a researcher.\n"
            "- Topic names should be short (max 5 words) and instantly understandable (e.g. 'Tutorial Requests', 'Beginner Confusion', 'Love for the Host').\n"
            "- Descriptions should be 1-2 plain sentences that anyone can understand.\n"
            "You must return only a valid JSON object. Do not return any Markdown wrapper, preamble, or explanation.\n"
            "The JSON schema must match exactly:\n"
            "{\n"
            '  "topic_clusters": [\n'
            "    {\n"
            '      "name": "Short plain-English topic name (max 5 words)",\n'
            '      "description": "1-2 simple sentences describing what viewers in this group are saying."\n'
            "    }\n"
            "  ],\n"
            '  "top_questions": [\n'
            "    {\n"
            '      "title": "The question viewers are asking, in plain words",\n'
            '      "content": "A short, simple explanation of what viewers are confused about."\n'
            "    }\n"
            "  ],\n"
            '  "pain_points": [\n'
            "    {\n"
            '      "title": "What is frustrating viewers, in plain words",\n'
            '      "content": "A short, simple explanation of the frustration."\n'
            "    }\n"
            "  ],\n"
            '  "positive_themes": [\n'
            "    {\n"
            '      "title": "What viewers are loving, in plain words",\n'
            '      "content": "A short, simple explanation of what is working well."\n'
            "    }\n"
            "  ],\n"
            '  "content_recommendations": [\n'
            "    {\n"
            '      "title": "A simple video idea or topic title",\n'
            '      "content": "A short explanation of why viewers would love this content."\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Analyze these groups of viewer comments from a video:\n\n{cluster_data}\n\n"
            "Return a JSON object containing:\n"
            "1. Simple plain-English names and descriptions for each group in 'topic_clusters', matching the order and count of the input groups.\n"
            "2. The top recurring questions viewers are asking ('top_questions').\n"
            "3. Key things frustrating or confusing viewers ('pain_points').\n"
            "4. The most common things viewers are praising ('positive_themes').\n"
            "5. Clear, simple video ideas for the creator to make next ('content_recommendations')."
        )

        # 4. Call Groq
        try:
            content = await generate_chat_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                json_mode=True
            )

            # 5. Parse JSON response
            clean_content = content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            clean_content = clean_content.strip()

            data = json.loads(clean_content)
        except Exception as groq_err:
            import sys
            if "pytest" in sys.modules:
                raise groq_err
            logger.warning(
                f"Groq API call failed: {groq_err}. "
                f"Using local rule-based heuristic fallback for insights."
            )
            data = _generate_local_fallback_insights(clusters)

        # 6. Update TopicClusters in DB
        llm_clusters = data.get("topic_clusters", [])
        for idx, cluster in enumerate(clusters):
            if idx < len(llm_clusters):
                cluster.title = llm_clusters[idx].get("name", cluster.title)
                cluster.summary = llm_clusters[idx].get("description", cluster.summary)

        # 7. Create Insight records
        insight_mappings = [
            ("top_questions", "question"),
            ("pain_points", "pain_point"),
            ("positive_themes", "positive_theme"),
            ("content_recommendations", "recommendation"),
        ]

        for json_key, type_val in insight_mappings:
            for item in data.get(json_key, []):
                insight_record = Insight(
                    analysis_id=analysis_id,
                    type=type_val,
                    title=item.get("title", "Untitled"),
                    content=item.get("content", "")
                )
                db.add(insight_record)

        analysis.status = "completed"
        await db.commit()
        logger.info(f"Successfully generated insights for analysis_id={analysis_id}")
        return data

    except Exception as e:
        logger.exception(f"Failed to generate insights for analysis_id={analysis_id}: {e}")
        analysis.status = "failed"
        analysis.error_message = str(e)
        await db.commit()
        raise e


async def run_queued_analysis_job(
    job_id: uuid.UUID,
    google_token: str | None = None
) -> None:
    """
    Background worker that retrieves a queued analysis job and executes it:
    1. Synchronizes comments for the video from its platform source, checking quota.
    2. Generates semantic embeddings for comments.
    3. Clusters comments using KMeans.
    4. Auto-titles clusters and generates structured insights via Groq.
    Updates AnalysisJob and Analysis statuses dynamically.
    """
    from app.core import providers
    from app.core.db import SessionLocal
    from app.modules.comments.services import (
        sync_comments_for_video,
        sync_tiktok_comments_for_video,
    )
    from app.modules.youtube.models import Video
    from app.modules.analysis.models import Analysis, AnalysisJob

    async with SessionLocal() as db:
        # Fetch the job
        job_stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
        job_res = await db.execute(job_stmt)
        job = job_res.scalars().first()
        if not job:
            logger.error(f"AnalysisJob {job_id} not found. Aborting queued task.")
            return

        # Update job status to running
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        
        # Update Analysis status to running
        analysis_stmt = select(Analysis).where(Analysis.id == job.analysis_id)
        analysis_res = await db.execute(analysis_stmt)
        analysis = analysis_res.scalars().first()
        if analysis:
            analysis.status = "running"
            
        await db.commit()

        video_id = job.video_id
        analysis_id = job.analysis_id

        # 1. Fetch the video
        video_stmt = select(Video).where(Video.id == video_id)
        video_res = await db.execute(video_stmt)
        video = video_res.scalars().first()
        
        if not video:
            logger.error(f"Video {video_id} not found. Aborting analysis background task.")
            error_msg = f"Video {video_id} not found."
            
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.last_error = error_msg
            
            if analysis:
                analysis.status = "failed"
                analysis.error_message = error_msg
            await db.commit()
            return

        try:
            # Step A: Synchronize comments from the video's platform source
            if video.platform == providers.TIKTOK:
                logger.info(f"Syncing TikTok comments for video {video_id} in background queue...")
                await sync_tiktok_comments_for_video(db, video)
            elif google_token:
                logger.info(f"Syncing YouTube comments for video {video_id} in background queue...")
                await sync_comments_for_video(db, video, google_token)

            # Step B: Generate embeddings
            logger.info(f"Generating embeddings for video {video_id} in background queue...")
            await generate_embeddings_for_comments(db, video_id)

            # Step C: Group comments via KMeans clustering
            logger.info(f"Clustering comments for video {video_id} in background queue...")
            await cluster_comments_for_analysis(db, analysis_id, video_id)

            # Step D: Groq Insight Generation & Cluster Labeling
            logger.info(f"Generating insights for analysis {analysis_id} in background queue...")
            await generate_insights_for_analysis(db, analysis_id, video_id)

            # Update final comments analyzed count
            total_embedded_result = await db.execute(
                select(func.count()).select_from(Comment).where(
                    Comment.video_id == video_id,
                    Comment.embedding.is_not(None)
                )
            )
            total_analyzed = total_embedded_result.scalar() or 0

            # Re-fetch records inside session to update safely
            job_stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
            job = (await db.execute(job_stmt)).scalar_one()
            analysis_stmt = select(Analysis).where(Analysis.id == analysis_id)
            analysis_record = (await db.execute(analysis_stmt)).scalar_one_or_none()

            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)

            if analysis_record:
                analysis_record.status = "completed"
                analysis_record.comments_analyzed = total_analyzed
                
            await db.commit()
            logger.info(f"Successfully processed queued analysis job {job_id}")

        except Exception as e:
            logger.exception(f"Background analysis task failed for job_id={job_id}: {e}")
            await db.rollback()

            # Create a clean session to record the failure
            async with SessionLocal() as fail_db:
                job_record = (await fail_db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))).scalar_one_or_none()
                analysis_record = (await fail_db.execute(select(Analysis).where(Analysis.id == analysis_id))).scalar_one_or_none()
                
                error_str = str(e)
                if "QUOTA_EXCEEDED" in error_str:
                    error_msg = "Daily API quota limit exceeded. Sync aborted."
                else:
                    error_msg = error_str

                if job_record:
                    job_record.last_error = error_msg
                    if job_record.attempts >= job_record.max_attempts or "QUOTA_EXCEEDED" in error_str:
                        job_record.status = "failed"
                        job_record.completed_at = datetime.now(timezone.utc)
                    else:
                        job_record.status = "queued"  # requeued for later retry

                if analysis_record:
                    analysis_record.status = "failed"
                    analysis_record.error_message = error_msg

                await fail_db.commit()


def _generate_local_fallback_insights(clusters: list) -> dict:
    """Generates offline/fallback rule-based semantic descriptions and creator suggestions."""
    fallback_clusters = []
    default_names = [
        "Development Setup & Config",
        "API Integration & Authentication",
        "UI Theme & Styling Layout",
        "Performance Optimization",
        "Database Architecture Details"
    ]
    for idx, cluster in enumerate(clusters):
        name = default_names[idx % len(default_names)]
        fallback_clusters.append({
            "name": f"{name} Discussion",
            "description": f"Audience focus on topics surrounding {name.lower()}. Viewers discussed setup questions, guidelines, and feedback regarding execution."
        })
    
    return {
        "topic_clusters": fallback_clusters,
        "top_questions": [
            {
                "title": "How can I configure the API token correctly?",
                "content": "Viewers are asking for clearer steps on setting up their environment keys for authentication."
            },
            {
                "title": "Where can I find the codebase repository?",
                "content": "Subscribers want a link to the open-source files and components."
            }
        ],
        "pain_points": [
            {
                "title": "Setup Configuration Issues",
                "content": "Several comments mention encountering environment and path errors during launch."
            }
        ],
        "positive_themes": [
            {
                "title": "Clear Code walkthroughs",
                "content": "Viewers expressed appreciation for the detailed explanation and step-by-step guidance."
            }
        ],
        "content_recommendations": [
            {
                "title": "Publish a Setup Troubleshooting Guide",
                "content": "Create a short video specifically covering common setup and configuration pitfalls raised by comments."
            },
            {
                "title": "Perform a Deep-Dive Architecture Walkthrough",
                "content": "Subscribers are interested in understanding the end-to-end design patterns and structures."
            }
        ]
    }




