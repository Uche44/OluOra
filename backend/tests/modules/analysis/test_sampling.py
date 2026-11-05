import uuid

from unittest.mock import MagicMock

from app.modules.comments.models import Comment
from app.modules.analysis.services import _cluster_digest, _select_cluster_samples


def _comment(text: str, embedding: list[float], likes: int = 0) -> MagicMock:
    comment = MagicMock(spec=Comment)
    comment.id = uuid.uuid4()
    comment.text = text
    comment.embedding = embedding
    comment.like_count = likes
    return comment


def test_select_cluster_samples_covers_subthemes():
    """A large cluster should sample both of its well-separated sub-themes."""
    comments = []
    for i in range(40):
        embedding = [1.0 + i * 0.001, 0.0] * 8
        comments.append(_comment(f"Group A comment {i} about pricing", embedding, likes=i))
    for i in range(40):
        embedding = [-1.0 - i * 0.001, 0.0] * 8
        comments.append(_comment(f"Group B comment {i} about tutorials", embedding, likes=i))

    sampled = _select_cluster_samples(comments, limit=20)

    assert len(sampled) == 20
    # Both sub-themes must be represented, not just one side of the cluster.
    assert any(comment.embedding[0] > 0 for comment in sampled)
    assert any(comment.embedding[0] < 0 for comment in sampled)


def test_select_cluster_samples_returns_all_when_small():
    comments = [_comment(f"Only comment {i}", [0.1] * 16) for i in range(4)]

    sampled = _select_cluster_samples(comments, limit=20)

    assert len(sampled) == 4
    assert {c.id for c in sampled} == {c.id for c in comments}


def test_select_cluster_samples_dedupes_and_respects_limit():
    comments = [
        _comment("This is a duplicate comment about pricing", [0.1] * 16),
        _comment("This is a duplicate comment about pricing", [0.1] * 16),
        _comment("A different comment about tutorials", [0.2] * 16),
    ]

    sampled = _select_cluster_samples(comments, limit=10)

    assert len(sampled) == 2


def test_cluster_digest_uses_all_comments():
    comments = [
        _comment("How much does the pricing plan cost?", [0.1] * 16),
        _comment("Is the pricing monthly or yearly?", [0.2] * 16),
        _comment("The pricing page confused me", [0.3] * 16),
        _comment("Pricing is too expensive", [0.4] * 16),
        _comment("I love the tutorial", [0.5] * 16),
        _comment("Great tutorial, thanks", [0.6] * 16),
    ]

    digest = _cluster_digest(comments)

    assert digest["total"] == 6
    assert digest["question_count"] == 2
    assert "pricing" in " ".join(digest["top_terms"])
