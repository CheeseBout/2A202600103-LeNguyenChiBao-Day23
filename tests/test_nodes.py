from langgraph_agent_lab.nodes import classify_node
from langgraph_agent_lab.state import Route


def test_classify_priority_risky_over_tool() -> None:
    result = classify_node({"query": "Please check order status and refund now"})
    assert result["route"] == Route.RISKY.value


def test_classify_missing_info_word_boundary() -> None:
    item_query = classify_node({"query": "Need item update soon"})
    vague_query = classify_node({"query": "Can you fix it?"})
    assert item_query["route"] != Route.MISSING_INFO.value
    assert vague_query["route"] == Route.MISSING_INFO.value


def test_classify_error_keywords() -> None:
    result = classify_node({"query": "Service crash and timeout happened"})
    assert result["route"] == Route.ERROR.value
