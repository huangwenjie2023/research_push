from research_push.config import load_all
from research_push.models import Item, parse_topics
from research_push.scoring import score_item


def test_topics_load():
    config = load_all()
    topics = parse_topics(config["topics"])
    assert {topic.id for topic in topics} == {
        "point_cloud_geometry_compression",
        "mesh_compression",
        "rl_guided_generation",
    }
    assert all(topic.daily_limit == 5 for topic in topics)


def test_point_cloud_item_scores_positive():
    config = load_all()
    topic = parse_topics(config["topics"])[0]
    item = Item(
        topic_id=topic.id,
        source_id="arxiv",
        title="Learned point cloud geometry compression with implicit neural representation",
        url="https://arxiv.org/abs/0000.00000",
        abstract="We propose an entropy model for point cloud compression with rate distortion optimization and open source code.",
        published_at="2026-05-30T00:00:00Z",
        pdf_url="https://arxiv.org/pdf/0000.00000",
        code_url="https://github.com/example/repo",
    )
    total, features, reasons = score_item(item, topic, config["scoring"])
    assert total > 5
    assert features["topic_relevance"] > 0
    assert reasons

