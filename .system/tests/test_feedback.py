from research_push.scoring import update_state_from_feedback


def test_feedback_updates_are_bounded():
    config = {
        "feedback": {
            "learning_rate": 0.12,
            "min_weight": 0.2,
            "max_weight": 3.0,
        }
    }
    state = {}
    for _ in range(40):
        update_state_from_feedback(state, "point cloud compression INR entropy model", "想多看类似", config)
    assert state["feature_multipliers"]["topic_relevance"] <= 3.0
    for _ in range(80):
        update_state_from_feedback(state, "point cloud compression INR entropy model", "想少看类似", config)
    assert state["feature_multipliers"]["topic_relevance"] >= 0.2

