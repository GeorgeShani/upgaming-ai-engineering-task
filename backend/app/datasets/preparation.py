import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .files import read_jsonl, sha256_file, write_json, write_jsonl
from .fixtures import load_fixtures, validate_cases
from .hotpot import context_documents
from .models import Document


def prepare_bundle(
    training_rows, selection: dict, fixture_dir: Path, output: Path, count: int, progress=None
) -> dict:
    if count < 1:
        raise ValueError("Passage count must be positive")
    if output.exists():
        raise FileExistsError(
            "Output already exists; choose a new directory to preserve the old run"
        )
    _, documents, fixture_manifest = load_fixtures(fixture_dir)
    revision = selection["revision"]
    if fixture_manifest["dataset_revision"] != revision:
        raise ValueError("Dataset selection and frozen evaluation use different revisions")
    hotpot_count = sum(doc.source.kind == "hotpotqa" for doc in documents.values())
    if hotpot_count > count:
        raise ValueError("Requested passage count is smaller than required evaluation support")
    duplicate_occurrences, rows_consumed = 0, 0
    if hotpot_count < count:
        for row in training_rows:
            rows_consumed += 1
            for doc in context_documents(row, revision, "train"):
                if doc.document_id in documents:
                    duplicate_occurrences += 1
                    continue
                documents[doc.document_id] = doc
                hotpot_count += 1
                if hotpot_count == count:
                    break
            if progress and rows_consumed % 1000 == 0:
                progress(rows_consumed, hotpot_count)
            if hotpot_count == count:
                break
    if hotpot_count != count:
        raise ValueError(
            f"Source exhausted: found {hotpot_count} unique HotpotQA passages, need {count}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="preparing-", dir=output.parent) as staging:
        directory = Path(staging)
        corpus = directory / "corpus.jsonl"
        write_jsonl(corpus, sorted(documents.values(), key=lambda doc: doc.document_id))
        manifest = {
            "schema_version": 1,
            "dataset": selection["dataset"],
            "configuration": selection["configuration"],
            "dataset_revision": revision,
            "normalization": selection["normalization"],
            "selection": selection["selection"],
            "license": selection["license"],
            "requested_hotpot_passages": count,
            "hotpot_passages": hotpot_count,
            "synthetic_passages": len(documents) - hotpot_count,
            "unique_source_records": len(documents),
            "training_rows_consumed": rows_consumed,
            "duplicate_occurrences_skipped": duplicate_occurrences,
            "meets_assignment_minimum": hotpot_count >= 50000,
            "corpus_sha256": sha256_file(corpus),
            "fixture_files": fixture_manifest["files"],
        }
        write_json(directory / "manifest.json", manifest)
        # Publish a whole directory only after every file is complete. Failed runs leave no bundle.
        directory.rename(output)
    return manifest


def verify_bundle(output: Path, fixture_dir: Path) -> dict:
    cases, _, fixture_manifest = load_fixtures(fixture_dir)
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    if manifest["fixture_files"] != fixture_manifest["files"]:
        raise ValueError("Bundle was prepared for a different set of evaluation fixtures")
    if manifest["dataset_revision"] != fixture_manifest["dataset_revision"]:
        raise ValueError("Bundle and evaluation fixture revisions differ")
    if sha256_file(output / "corpus.jsonl") != manifest["corpus_sha256"]:
        raise ValueError("Corpus hash mismatch")
    support_ids = {item.document_id for case in cases for item in case.evidence}
    support_documents, seen_ids, seen_hashes = {}, set(), set()
    counts = {"hotpotqa": 0, "synthetic": 0}
    for doc in read_jsonl(output / "corpus.jsonl", Document):
        if doc.document_id in seen_ids or doc.content_sha256 in seen_hashes:
            raise ValueError("Corpus contains duplicate source records")
        if doc.source.kind == "hotpotqa" and doc.source.revision != manifest["dataset_revision"]:
            raise ValueError("Corpus contains an unexpected source revision")
        seen_ids.add(doc.document_id)
        seen_hashes.add(doc.content_sha256)
        counts[doc.source.kind] += 1
        if doc.document_id in support_ids:
            support_documents[doc.document_id] = doc
    expected = {
        "hotpotqa": manifest["hotpot_passages"],
        "synthetic": manifest["synthetic_passages"],
    }
    if counts != expected or len(seen_ids) != manifest["unique_source_records"]:
        raise ValueError("Corpus record counts differ from the manifest")
    if counts["hotpotqa"] != manifest["requested_hotpot_passages"]:
        raise ValueError("Corpus does not contain the requested number of HotpotQA passages")
    meets_minimum = counts["hotpotqa"] >= 50000
    if meets_minimum != manifest["meets_assignment_minimum"]:
        raise ValueError("Assignment minimum flag does not match the actual source count")
    validate_cases(cases, support_documents)
    return {
        "verified": True,
        "dataset_revision": manifest["dataset_revision"],
        "unique_source_records": len(seen_ids),
        "hotpot_passages": counts["hotpotqa"],
        "synthetic_passages": counts["synthetic"],
        "evaluation_cases": len(cases),
        "meets_assignment_minimum": meets_minimum,
        "corpus_sha256": manifest["corpus_sha256"],
        "corpus_bytes": (output / "corpus.jsonl").stat().st_size,
        "final_cases": sum(case.split == "final" for case in cases),
        "development_cases": sum(case.split == "development" for case in cases),
        "reference_review": fixture_manifest["reference_review"],
    }
