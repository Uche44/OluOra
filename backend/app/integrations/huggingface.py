import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generates semantic text embeddings using the Hugging Face Inference API.

    Accepts a list of text strings and returns a list of float vectors.
    Requests are batched up to BATCH_SIZE items per call to stay within
    Hugging Face API rate limits.

    Args:
        texts: A list of clean, preprocessed text strings to embed.

    Returns:
        A list of float vectors (one per input text).

    Raises:
        ValueError: If HF_API_KEY is not configured.
        Exception: If the HF Inference API returns a non-200 response.
    """
    if not settings.HF_API_KEY:
        raise ValueError("HF_API_KEY is not configured in settings.")

    if not texts:
        return []

    model = settings.HF_EMBEDDING_MODEL
    api_url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {
        "Authorization": f"Bearer {settings.HF_API_KEY}",
        "Content-Type": "application/json"
    }

    all_embeddings: list[list[float]] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for batch_start in range(0, len(texts), BATCH_SIZE):
            batch = texts[batch_start: batch_start + BATCH_SIZE]
            batch_num = batch_start // BATCH_SIZE + 1

            payload = {
                "inputs": batch,
                # wait_for_model=True retries if the model is still loading on HF servers
                "options": {"wait_for_model": True}
            }

            try:
                response = await client.post(api_url, headers=headers, json=payload)

                if response.status_code != 200:
                    logger.error(
                        f"HF Inference API error. Status={response.status_code}, "
                        f"Model={model}, Body={response.text}"
                    )
                    raise Exception(
                        f"Hugging Face API request failed with status "
                        f"{response.status_code}: {response.text}"
                    )

                batch_result = response.json()

                # HF returns a list of vectors (one per input text in the batch)
                if not isinstance(batch_result, list):
                    raise Exception(
                        f"Unexpected response format from HF API: {type(batch_result)}"
                    )

                all_embeddings.extend(batch_result)
                logger.info(
                    f"Generated embeddings for batch {batch_num} "
                    f"size={len(batch)}, model={model}"
                )

            except httpx.TimeoutException:
                logger.error(
                    f"HF Inference API request timed out at batch {batch_num}"
                )
                raise
            except Exception as e:
                logger.error(f"Error generating embeddings from HF API: {e}")
                raise

    return all_embeddings
