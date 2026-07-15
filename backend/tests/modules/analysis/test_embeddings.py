import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── generate_embeddings (HF integration) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_embeddings_returns_vectors():
    """Should return one float vector per input text."""
    mock_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

    with patch("app.integrations.huggingface.settings") as mock_settings, \
         patch("app.integrations.huggingface.httpx.AsyncClient") as mock_client_class:

        mock_settings.HF_API_KEY = "hf_test_key"
        mock_settings.HF_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_vectors

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        from app.integrations.huggingface import generate_embeddings
        result = await generate_embeddings(["This is a test comment.", "Another comment here."])

    assert result == mock_vectors
    assert len(result) == 2
    assert all(isinstance(v, list) for v in result)


@pytest.mark.asyncio
async def test_generate_embeddings_empty_input():
    """Should return an empty list if no texts are provided."""
    with patch("app.integrations.huggingface.settings") as mock_settings:
        mock_settings.HF_API_KEY = "hf_test_key"
        mock_settings.HF_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

        from app.integrations.huggingface import generate_embeddings
        result = await generate_embeddings([])

    assert result == []


@pytest.mark.asyncio
async def test_generate_embeddings_raises_on_missing_key():
    """Should raise ValueError if HF_API_KEY is not set."""
    with patch("app.integrations.huggingface.settings") as mock_settings:
        mock_settings.HF_API_KEY = ""
        mock_settings.HF_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

        from app.integrations.huggingface import generate_embeddings
        with pytest.raises(ValueError, match="HF_API_KEY is not configured"):
            await generate_embeddings(["some text"])


@pytest.mark.asyncio
async def test_generate_embeddings_raises_on_api_error():
    """Should raise Exception if the HF API returns a non-200 status."""
    with patch("app.integrations.huggingface.settings") as mock_settings, \
         patch("app.integrations.huggingface.httpx.AsyncClient") as mock_client_class:

        mock_settings.HF_API_KEY = "hf_test_key"
        mock_settings.HF_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_response.json.return_value = {"error": "model loading"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        from app.integrations.huggingface import generate_embeddings
        with pytest.raises(Exception, match="Hugging Face API request failed"):
            await generate_embeddings(["some text"])


# ─── generate_embeddings_for_comments (analysis service) ─────────────────────

@pytest.mark.asyncio
async def test_generate_embeddings_for_comments_skips_already_embedded():
    """Should return 0 and skip processing if all comments are already embedded."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []  # no unembedded comments
    mock_db.execute = AsyncMock(return_value=mock_result)

    from app.modules.analysis.services import generate_embeddings_for_comments
    count = await generate_embeddings_for_comments(mock_db, uuid.uuid4())

    assert count == 0
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_generate_embeddings_for_comments_saves_vectors():
    """Should embed unembedded comments and commit vectors to the database.

    db.execute call order:
      [0] SELECT comments without embeddings -> 2 comments
      [1] UPDATE comment_a (embedding + sentiment)
      [2] UPDATE comment_b (embedding + sentiment)
      [3] SELECT already-embedded with NULL sentiment -> empty (backfill finds nothing)
    Commit is called exactly once (after UPDATEs; backfill has no work to do).
    """
    video_id = uuid.uuid4()

    mock_comment_a = MagicMock()
    mock_comment_a.id = uuid.uuid4()
    mock_comment_a.text = "This is a great video about databases."
    mock_comment_a.embedding = None

    mock_comment_b = MagicMock()
    mock_comment_b.id = uuid.uuid4()
    mock_comment_b.text = "I learned so much about SQLAlchemy from this."
    mock_comment_b.embedding = None

    mock_db = AsyncMock()

    embed_result = MagicMock()
    embed_result.scalars.return_value.all.return_value = [mock_comment_a, mock_comment_b]
    update_result = MagicMock()
    backfill_result = MagicMock()
    backfill_result.scalars.return_value.all.return_value = []

    # [0] SELECT to-embed, [1] UPDATE a, [2] UPDATE b, [3] SELECT backfill
    mock_db.execute = AsyncMock(side_effect=[
        embed_result,
        update_result,
        update_result,
        backfill_result,
    ])

    mock_vectors = [[0.1] * 384, [0.2] * 384]

    with patch(
        "app.modules.analysis.services.generate_embeddings",
        new_callable=AsyncMock,
        return_value=mock_vectors
    ):
        from app.modules.analysis.services import generate_embeddings_for_comments
        count = await generate_embeddings_for_comments(mock_db, video_id)

    assert count == 2
    mock_db.commit.assert_called_once()
