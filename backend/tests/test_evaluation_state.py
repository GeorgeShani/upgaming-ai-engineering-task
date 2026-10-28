import pytest
from app.evaluation.state import attempt_order, exclusive_run, load_or_create, recover_pending, save


def test_identity_drift_is_rejected_and_inflight_work_is_not_repeated(tmp_path):
    path = tmp_path / "manifest.json"
    assert load_or_create(path, {"identity": "original"}) == {"identity": "original"}
    with pytest.raises(ValueError, match="identity"):
        load_or_create(path, {"identity": "changed"})
    pending = tmp_path / "case-a.pending.json"
    save(pending, {"case_id": "case", "strategy": "a", "ledger_before": {"calls": 1}})
    recovered = recover_pending(tmp_path, {"calls": 2})
    assert recovered[0]["error"] == "interrupted_uncertain"
    assert (tmp_path / "case-a.json").is_file()
    assert not pending.exists()
    assert recover_pending(tmp_path, {"calls": 2}) == []


def test_only_one_runner_can_hold_the_output_directory(tmp_path):
    with exclusive_run(tmp_path):
        with pytest.raises(ValueError, match="running"):
            with exclusive_run(tmp_path):
                pytest.fail("Concurrent evaluator acquired the lock")
    with exclusive_run(tmp_path):
        pass


def test_config_order_alternates_without_changing_case_order():
    assert attempt_order(["one", "two"]) == [("one", "a"), ("one", "b"), ("two", "b"), ("two", "a")]
