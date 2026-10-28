import pytest
from app.evaluation.state import save
from app.evaluation_cli import selection_for
from test_evaluation_scoring import case, result


def test_selection_requires_complete_development_and_cannot_be_changed_after_final(tmp_path):
    sample = case("simple")
    sample.case_id, sample.split = "development-simple-01", "development"
    manifest = {"identity": "frozen"}
    canonical = {"one": "🚀 11 minutes"}
    with pytest.raises(ValueError, match="every development"):
        selection_for(tmp_path, manifest, [sample], canonical)
    for strategy in ("a", "b"):
        save(
            tmp_path / "development" / f"{sample.case_id}-{strategy}.json",
            {
                "case_id": sample.case_id,
                "strategy": strategy,
                "result": result(),
                "elapsed_ms": 10,
            },
        )
    save(tmp_path / "final" / "final-simple-01-a.json", {})
    with pytest.raises(ValueError, match="after final"):
        selection_for(tmp_path, manifest, [sample], canonical)
    (tmp_path / "final" / "final-simple-01-a.json").unlink()
    selected = selection_for(tmp_path, manifest, [sample], canonical)
    assert selected["selected_strategy"] == "a"
    assert selection_for(tmp_path, manifest, [sample], canonical) == selected
    save(
        tmp_path / "development" / f"{sample.case_id}-a.json",
        {
            "case_id": sample.case_id,
            "strategy": "a",
            "result": None,
        },
    )
    with pytest.raises(ValueError, match="after configuration selection"):
        selection_for(tmp_path, manifest, [sample], canonical)
