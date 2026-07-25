import pytest
from unittest.mock import MagicMock, patch
from pipeline.classification_orchestrator import ClassificationOrchestrator


@pytest.fixture
def mock_orchestrator():
    with patch(
        "pipeline.classification_orchestrator.RuleClassifier"
    ) as mock_rule, patch(
        "pipeline.classification_orchestrator.MLClassifier"
    ) as mock_ml, patch(
        "pipeline.classification_orchestrator.LLMClassifier"
    ) as mock_llm:

        rule_inst = MagicMock()
        ml_inst = MagicMock()
        llm_inst = MagicMock()

        mock_rule.return_value = rule_inst
        mock_ml.return_value = ml_inst
        mock_llm.return_value = llm_inst

        orch = ClassificationOrchestrator("dummy_config.yaml")
        return orch, rule_inst, ml_inst, llm_inst


def test_cascade_rule_match(mock_orchestrator):
    orch, rule_inst, ml_inst, llm_inst = mock_orchestrator

    # Rule succeeds
    rule_inst.predict_batch.return_value = [("Food", 1.0, "rule")]

    txns = [{"description": "SWIGGY BANGALORE"}]
    res = orch.process_batch(txns)

    assert res[0]["category"] == "Food"
    assert res[0]["classification_method"] == "rule"
    rule_inst.predict_batch.assert_called_once_with(["SWIGGY BANGALORE"])
    ml_inst.predict_batch.assert_not_called()
    llm_inst.predict_batch.assert_not_called()


def test_cascade_ml_match(mock_orchestrator):
    orch, rule_inst, ml_inst, llm_inst = mock_orchestrator

    # Rule fails, ML succeeds
    rule_inst.predict_batch.return_value = [(None, 0.0, "none")]
    ml_inst.predict_batch.return_value = [("Shopping", 0.85, "ml")]

    txns = [{"description": "AMAZON RETAIL"}]
    res = orch.process_batch(txns)

    assert res[0]["category"] == "Shopping"
    assert res[0]["classification_method"] == "ml"
    rule_inst.predict_batch.assert_called_once_with(["AMAZON RETAIL"])
    ml_inst.predict_batch.assert_called_once_with(["AMAZON RETAIL"])
    llm_inst.predict_batch.assert_not_called()


def test_cascade_llm_match(mock_orchestrator):
    orch, rule_inst, ml_inst, llm_inst = mock_orchestrator

    # Rule and ML fail, LLM succeeds
    rule_inst.predict_batch.return_value = [(None, 0.0, "none")]
    ml_inst.predict_batch.return_value = [(None, 0.0, "none")]
    llm_inst.predict_batch.return_value = [("Entertainment", 0.9, "llm")]

    txns = [{"description": "NETFLIX SUB"}]
    res = orch.process_batch(txns)

    assert res[0]["category"] == "Entertainment"
    assert res[0]["classification_method"] == "llm"
    rule_inst.predict_batch.assert_called_once()
    ml_inst.predict_batch.assert_called_once()
    llm_inst.predict_batch.assert_called_once()


def test_cascade_all_fail(mock_orchestrator):
    orch, rule_inst, ml_inst, llm_inst = mock_orchestrator

    # All fail
    rule_inst.predict_batch.return_value = [(None, 0.0, "none")]
    ml_inst.predict_batch.return_value = [(None, 0.0, "none")]
    llm_inst.predict_batch.return_value = [("Others", 0.0, "llm")]

    txns = [{"description": "UNKNOWN MYSTERY"}]
    res = orch.process_batch(txns)

    assert res[0]["category"] == "Uncategorized"
    assert res[0]["classification_method"] == "none"


def test_memo_cache_deduplication(mock_orchestrator):
    orch, rule_inst, ml_inst, llm_inst = mock_orchestrator

    rule_inst.predict_batch.return_value = [("Food", 1.0, "rule")]

    # Batch with two identical descriptions (case insensitive)
    txns = [{"description": "swiggy order 1"}, {"description": "SWIGGY ORDER 1"}]
    res = orch.process_batch(txns)

    assert res[0]["category"] == "Food"
    assert res[1]["category"] == "Food"
    # predict_batch should only be called once with unique key
    rule_inst.predict_batch.assert_called_once_with(["SWIGGY ORDER 1"])
