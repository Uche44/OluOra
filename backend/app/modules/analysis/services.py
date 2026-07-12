import os
# Silence joblib wmic warning on Windows when logical core count lookup fails
os.environ["LOKY_MAX_CPU_COUNT"] = "4"

import uuid
import logging
import numpy as np
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.comments.models import Comment
from app.modules.comments.preprocessing import clean_comment_text
from app.integrations.huggingface import generate_embeddings
from app.integrations.groq import generate_chat_completion

logger = logging.getLogger(__name__)


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

    # 4. Save each embedding back to the corresponding Comment row
    for comment, vector in zip(comments_to_embed, embeddings):
        await db.execute(
            update(Comment)
            .where(Comment.id == comment.id)
            .values(embedding=vector)
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
                f"CLUSTER {idx + 1}:\n"
                f"Size: {cluster.size} comments\n"
                f"Average Sentiment: {cluster.sentiment_score:.2f}\n"
                f"Representative Comments:\n{rep_lines}\n"
            )
            cluster_blocks.append(block)

        cluster_data = "\n---\n".join(cluster_blocks)

        # 3. Construct prompts
        system_prompt = (
            "You are an expert audience intelligence analyst. Your job is to analyze clusters of comments "
            "from a video and synthesize them into structured insights.\n"
            "You must return only a valid JSON object. Do not return any Markdown wrapper, preamble, or explanation.\n"
            "The JSON schema must match exactly:\n"
            "{\n"
            '  "topic_clusters": [\n'
            "    {\n"
            '      "name": "Short Cluster Name (max 5 words)",\n'
            '      "description": "1-2 sentence description summarizing the main theme, sentiment, and details of this cluster."\n'
            "    }\n"
            "  ],\n"
            '  "top_questions": [\n'
            "    {\n"
            '      "title": "Specific question asked by viewers",\n'
            '      "content": "Short explanation of viewer confusion or details about the question."\n'
            "    }\n"
            "  ],\n"
            '  "pain_points": [\n'
            "    {\n"
            '      "title": "Summary of the pain point",\n'
            '      "content": "Explanation of what is frustrating or confusing the viewers."\n'
            "    }\n"
            "  ],\n"
            '  "positive_themes": [\n'
            "    {\n"
            '      "title": "Summary of praise or positive feedback",\n'
            '      "content": "Explanation of what viewers loved or found helpful."\n'
            "    }\n"
            "  ],\n"
            '  "content_recommendations": [\n'
            "    {\n"
            '      "title": "Suggested video topic or title",\n'
            '      "content": "Explanation of why this content should be created next and what it should address."\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Analyze these comment clusters from a video:\n\n{cluster_data}\n\n"
            "Return a JSON object containing:\n"
            "1. Re-labeled cluster names and descriptions in 'topic_clusters' matching the order and count of the input clusters.\n"
            "2. The top recurring questions ('top_questions').\n"
            "3. Key viewer frustrations/pain points ('pain_points').\n"
            "4. The most common positive themes ('positive_themes').\n"
            "5. Clear content recommendations for the creator ('content_recommendations')."
        )

        # 4. Call Groq
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


async def run_end_to_end_analysis(
    analysis_id: uuid.UUID,
    video_id: uuid.UUID,
    google_token: str | None = None
) -> None:
    """
    Background worker that executes the entire comments analysis pipeline:
    1. Synchronizes YouTube comments for the video (if a token is provided).
    2. Generates semantic embeddings for comments.
    3. Clusters comments using KMeans.
    4. Auto-titles clusters and generates structured insights via Groq.
    """
    from app.core.db import SessionLocal
    from app.modules.comments.services import sync_comments_for_video
    from app.modules.youtube.models import Video
    from app.modules.analysis.models import Analysis

    async with SessionLocal() as db:
        # 1. Fetch the video
        video_result = await db.execute(
            select(Video).where(Video.id == video_id)
        )
        video = video_result.scalars().first()
        if not video:
            logger.error(f"Video {video_id} not found. Aborting analysis background task.")
            # Set status to failed
            analysis_result = await db.execute(
                select(Analysis).where(Analysis.id == analysis_id)
            )
            analysis = analysis_result.scalars().first()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = f"Video {video_id} not found."
                await db.commit()
            return

        try:
            # Step A: Synchronize YouTube comments (if token provided)
            if google_token:
                logger.info(f"Syncing comments for video {video_id} in background...")
                await sync_comments_for_video(db, video, google_token)

            # Step B: Generate embeddings
            logger.info(f"Generating embeddings for video {video_id} in background...")
            embedded_count = await generate_embeddings_for_comments(db, video_id)

            # Step C: Group comments via KMeans clustering
            logger.info(f"Clustering comments for video {video_id} in background...")
            await cluster_comments_for_analysis(db, analysis_id, video_id)

            # Step D: Groq Insight Generation & Cluster Labeling
            logger.info(f"Generating insights for analysis {analysis_id} in background...")
            await generate_insights_for_analysis(db, analysis_id, video_id)

            # Update final comments analyzed count
            analysis_result = await db.execute(
                select(Analysis).where(Analysis.id == analysis_id)
            )
            analysis_record = analysis_result.scalars().first()
            if analysis_record:
                analysis_record.comments_analyzed = embedded_count
                await db.commit()

        except Exception as e:
            logger.exception(f"Background analysis task failed for analysis_id={analysis_id}: {e}")
            analysis_result = await db.execute(
                select(Analysis).where(Analysis.id == analysis_id)
            )
            analysis_record = analysis_result.scalars().first()
            if analysis_record and analysis_record.status != "failed":
                analysis_record.status = "failed"
                analysis_record.error_message = str(e)
                await db.commit()



