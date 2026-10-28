"""Free offline score/integrity reproduction. No credentials, cloud requests or model calls."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.datasets.files import sha256_file
from app.datasets.fixtures import load_fixtures
from app.evaluation.context import digest
from app.evaluation.reporting import select_strategy, summarize
from app.evaluation.state import save
from app.evaluation_cli import records_for
from app.retrieval.chunking import chunk_spans


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify(archive, prepared):
    cases, fixture_documents, fixture_manifest = load_fixtures(Path("fixtures"))
    manifest, selection = read(archive / "manifest.json"), read(archive / "selection.json")
    assert manifest["identity"] == digest(manifest["details"]), "Manifest identity mismatch"
    local = manifest["details"]["code_and_local"]["local"]
    assert fixture_manifest["files"] == local["fixture_files"], "Frozen fixture hashes changed"
    assert sha256_file(prepared / "corpus.jsonl") == local["verification"]["corpus_sha256"], (
        "Corpus hash changed"
    )
    canonical = {}
    with (prepared / "corpus.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            document = json.loads(line)
            canonical[document["document_id"]] = document["text"]
    reports, records, all_rows = {}, {}, []
    for split in ("development", "final"):
        selected = [case for case in cases if case.split == split]
        rows = records_for(archive / split, selected)
        assert len(rows) == len(selected) * 2, f"Incomplete {split} attempts"
        summaries, scores = summarize(rows, {case.case_id: case for case in selected}, canonical)
        archived = read(archive / split / "summary.json")
        assert summaries == archived["strategies"], f"{split} summary does not reproduce"
        assert scores == read(archive / split / "scores.json"), f"{split} scores do not reproduce"
        checkpoint = read(archive / split / "checkpoint.json")
        assert checkpoint["identity"] == manifest["identity"] and checkpoint["corpus_consistent"]
        assert checkpoint["cloud"] == manifest["details"]["cloud"], "Cloud identity drift"
        records[split] = rows
        all_rows.extend(rows)
        reports[split] = {
            "attempts": len(rows),
            "summary_reproduced": True,
            "scores_reproduced": True,
            "errors": sum(row.get("result") is None for row in rows),
        }
    assert selection["identity"] == manifest["identity"]
    assert digest(records["development"]) == selection["development_receipts_sha256"]
    assert (
        select_strategy(read(archive / "development" / "summary.json")["strategies"])
        == selection["selected_strategy"]
    )
    final_start = min(datetime.fromisoformat(row["started_at"]) for row in records["final"])
    assert datetime.fromisoformat(selection["created_at"]) < final_start, (
        "Selection occurred after final testing"
    )
    for row in all_rows:
        result = row.get("result")
        if result:
            config = result["configuration"]
            frozen = manifest["details"]["code_and_local"]["settings"]
            assert config["strategy"] == row["strategy"]
            assert all(
                config[key] == frozen[key]
                for key in ("generation_model", "embedding_model", "embedding_dimensions")
            )
            assert result["execution"]["searches"] <= 3 and result["execution"]["llm_calls"] <= 3
    before = manifest["ledger_before"]
    continuity = all(
        previous["ledger_after"] == current["ledger_before"]
        for previous, current in zip(all_rows, all_rows[1:], strict=False)
    )
    after = read(archive / "final" / "checkpoint.json")["ledger_after"]
    assert after["reserved_usd"] < 4.5 and after["estimated_actual_usd"] < 5
    code_differences = [
        name
        for name, expected in manifest["details"]["code_and_local"]["code_files"].items()
        if sha256_file(Path(name)) != expected
    ]
    hashes = archive / "archive-hashes.json"
    if hashes.exists():
        for name, expected in read(hashes).items():
            assert sha256_file(archive / name) == expected, f"Archive file changed: {name}"
    chunk_comparison = {}
    for split in ("development", "final"):
        required = {e.document_id for case in cases if case.split == split for e in case.evidence}
        identical = 0
        for key in required:
            doc = fixture_documents[key]
            spans = [(segment.start, segment.end) for segment in doc.segments]
            identical += chunk_spans(doc.text, "a", spans) == chunk_spans(doc.text, "b", spans)
        chunk_comparison[split] = {
            "required_distinct_sources": len(required),
            "identical_spans": identical,
        }
    pairs = {}
    for row in records["final"]:
        pairs.setdefault(row["case_id"], {})[row["strategy"]] = row.get("result")
    successful_pairs = [pair for pair in pairs.values() if pair["a"] and pair["b"]]
    return {
        "scope": "offline archive reproduction; no provider requests",
        "identity": manifest["identity"],
        "splits": reports,
        "selected_strategy": selection["selected_strategy"],
        "selection_before_final": True,
        "first_final_attempt_at": final_start.isoformat(),
        "selection_at": selection["created_at"],
        "ledger_continuous_between_attempts": continuity,
        "ledger_before": before,
        "ledger_after": after,
        "code_bytes_match": not code_differences,
        "different_code_bytes": code_differences,
        "code_hash_note": (
            "Raw byte hashes can differ with checkout line endings; "
            "score equality is checked independently."
        ),
        "archive_hashes_checked": hashes.exists(),
        "required_source_chunk_comparison": chunk_comparison,
        "paired_successful_final_cases": len(successful_pairs),
        "paired_successes_with_identical_initial_queries": sum(
            pair["a"]["search_trace"][0]["query"] == pair["b"]["search_trace"][0]["query"]
            for pair in successful_pairs
        ),
        "george_independent_review": "pending",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("docs/evaluation"))
    parser.add_argument("--prepared", type=Path, default=Path("data/prepared"))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify(args.archive, args.prepared)
    if args.report:
        save(args.report, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
