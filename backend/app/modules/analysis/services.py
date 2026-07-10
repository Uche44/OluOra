import uuid
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.comments.models import Comment
from app.modules.comments.preprocessing import clean_comment_text
from app.integrations.huggingface import generate_embeddings

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
