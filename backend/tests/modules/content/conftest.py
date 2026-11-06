import pytest


@pytest.fixture(autouse=True)
def mock_content_embeddings(monkeypatch):
    """Keep content tests off the network.

    Opportunity generation may run a semantic check on cited comments. Return
    identical vectors by default so the check keeps evidence unless a test
    explicitly overrides it.
    """

    async def fake_embeddings(texts, allow_fallback=True):
        return [[1.0] + [0.0] * 7 for _ in texts]

    monkeypatch.setattr(
        "app.modules.content.services.generate_embeddings", fake_embeddings
    )
