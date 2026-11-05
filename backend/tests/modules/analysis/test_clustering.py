import uuid
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from app.modules.comments.models import Comment


@pytest.mark.asyncio
async def test_cluster_comments_no_comments():
    """Should return 0 clusters if there are no comments for the video."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    from app.modules.analysis.services import cluster_comments_for_analysis
    k = await cluster_comments_for_analysis(mock_db, uuid.uuid4(), uuid.uuid4())

    assert k == 0
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_cluster_comments_successful_partitioning():
    """Should partition comments into groups and record membership correctly."""
    analysis_id = uuid.uuid4()
    video_id = uuid.uuid4()

    # Generate 6 mock comments with 384-dimensional embeddings
    # Group A: embeddings around [1, 1, 1...]
    # Group B: embeddings around [-1, -1, -1...]
    comments = []
    for i in range(3):
        c = MagicMock(spec=Comment)
        c.id = uuid.uuid4()
        c.author_name = f"User A{i}"
        c.text = f"Love this video content theme A{i}"
        c.embedding = [1.0 + i * 0.01] * 384
        c.sentiment_score = 0.8
        comments.append(c)

    for i in range(3):
        c = MagicMock(spec=Comment)
        c.id = uuid.uuid4()
        c.author_name = f"User B{i}"
        c.text = f"Hate this feature theme B{i}"
        c.embedding = [-1.0 - i * 0.01] * 384
        c.sentiment_score = -0.5
        comments.append(c)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = comments
    mock_db.execute.return_value = mock_result

    # Mock DB add and flush behavior to assign fake cluster IDs
    added_clusters = []
    added_memberships = []

    def mock_add(instance):
        from app.modules.analysis.models import TopicCluster, CommentClusterMembership
        if isinstance(instance, TopicCluster):
            added_clusters.append(instance)
        elif isinstance(instance, CommentClusterMembership):
            added_memberships.append(instance)

    async def mock_flush():
        for cluster in added_clusters:
            if not getattr(cluster, "id", None):
                cluster.id = uuid.uuid4()

    mock_db.add = mock_add
    mock_db.flush = mock_flush

    from app.modules.analysis.services import cluster_comments_for_analysis
    # Cluster into 2 groups
    k = await cluster_comments_for_analysis(mock_db, analysis_id, video_id, num_clusters=2)

    assert k == 2
    assert len(added_clusters) == 2
    mock_db.commit.assert_called_once()

    # Check partition sizing
    sizes = [c.size for c in added_clusters]
    assert sorted(sizes) == [3, 3]

    # Check sentiment averages (one cluster positive, one negative)
    sentiments = [c.sentiment_score for c in added_clusters]
    assert any(abs(s - (-0.5)) < 1e-6 for s in sentiments)
    assert any(abs(s - 0.8) < 1e-6 for s in sentiments)

    # Every comment should be recorded against this analysis run, with the
    # cluster it was assigned to and its distance from the centroid.
    assert len(added_memberships) == len(comments)
    cluster_ids = {c.id for c in added_clusters}
    comment_ids = {c.id for c in comments}
    for membership in added_memberships:
        assert membership.analysis_id == analysis_id
        assert membership.cluster_id in cluster_ids
        assert membership.comment_id in comment_ids
        assert membership.distance is not None


@pytest.mark.asyncio
async def test_cluster_comments_fewer_comments_than_clusters():
    """Should restrict number of clusters to len(comments) if comments < num_clusters."""
    analysis_id = uuid.uuid4()
    video_id = uuid.uuid4()

    # Only 2 comments with distinct embeddings to prevent KMeans collapse
    comments = []
    for i in range(2):
        c = MagicMock(spec=Comment)
        c.id = uuid.uuid4()
        c.author_name = f"User {i}"
        c.text = f"Comment {i}"
        c.embedding = [0.1 if i == 0 else -0.1] * 384
        c.sentiment_score = 0.0
        comments.append(c)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = comments
    mock_db.execute.return_value = mock_result

    added_clusters = []

    def mock_add(instance):
        from app.modules.analysis.models import TopicCluster
        if isinstance(instance, TopicCluster):
            added_clusters.append(instance)

    mock_db.add = mock_add

    from app.modules.analysis.services import cluster_comments_for_analysis
    # Request 5 clusters, but should only create 2 since we only have 2 comments
    k = await cluster_comments_for_analysis(mock_db, analysis_id, video_id, num_clusters=5)

    assert k == 2
    assert len(added_clusters) == 2


@pytest.mark.asyncio
async def test_cluster_memberships_are_scoped_per_analysis():
    """Re-running clustering for a new analysis must not reuse the old run's rows."""
    video_id = uuid.uuid4()

    comments = []
    for i in range(4):
        c = MagicMock(spec=Comment)
        c.id = uuid.uuid4()
        c.author_name = f"User {i}"
        c.text = f"Distinct comment number {i} about pricing"
        c.embedding = ([1.0 if i < 2 else -1.0] * 16)
        c.sentiment_score = 0.0
        comments.append(c)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = comments
    mock_db.execute.return_value = mock_result

    from app.modules.analysis.models import TopicCluster, CommentClusterMembership

    captured = []

    def mock_add(instance):
        if isinstance(instance, (TopicCluster, CommentClusterMembership)):
            captured.append(instance)

    async def mock_flush():
        for instance in captured:
            if isinstance(instance, TopicCluster) and not getattr(instance, "id", None):
                instance.id = uuid.uuid4()

    mock_db.add = mock_add
    mock_db.flush = mock_flush

    from app.modules.analysis.services import cluster_comments_for_analysis

    first_analysis = uuid.uuid4()
    await cluster_comments_for_analysis(mock_db, first_analysis, video_id, num_clusters=2)
    first_memberships = [i for i in captured if isinstance(i, CommentClusterMembership)]
    assert len(first_memberships) == len(comments)
    assert all(m.analysis_id == first_analysis for m in first_memberships)

    captured.clear()

    second_analysis = uuid.uuid4()
    await cluster_comments_for_analysis(mock_db, second_analysis, video_id, num_clusters=2)
    second_memberships = [i for i in captured if isinstance(i, CommentClusterMembership)]
    assert len(second_memberships) == len(comments)
    assert all(m.analysis_id == second_analysis for m in second_memberships)
