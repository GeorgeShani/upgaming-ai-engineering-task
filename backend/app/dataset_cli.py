"""Run from the repository root: python -m backend.app.dataset_cli --help."""

import argparse
import json
from pathlib import Path

from .datasets.files import write_json
from .datasets.fixtures import freeze_fixtures, load_fixtures, render_review
from .datasets.hotpot import stream_rows
from .datasets.preparation import prepare_bundle, verify_bundle

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare reproducible source and evaluation data")
    parser.add_argument("--fixtures", type=Path, default=ROOT / "fixtures")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("freeze-fixtures", help="Create frozen labels once; refuses existing files")
    prepare = commands.add_parser(
        "prepare", help="Extract source passages without labels or model calls"
    )
    prepare.add_argument(
        "--count", type=int, help="Override the selection file's target passage count"
    )
    prepare.add_argument("--output", type=Path, default=ROOT / "data" / "prepared")
    verify = commands.add_parser(
        "verify", help="Check hashes, counts, source locations, and gold support"
    )
    verify.add_argument("--output", type=Path, default=ROOT / "data" / "prepared")
    verify.add_argument(
        "--report", type=Path, help="Write a small verification report without corpus text"
    )
    review = commands.add_parser(
        "review", help="Render frozen questions and evidence for human review"
    )
    review.add_argument("--output", type=Path, default=ROOT / "docs" / "evaluation-fixtures.md")
    args = parser.parse_args()
    try:
        if args.command == "verify":
            result = verify_bundle(args.output, args.fixtures)
            if args.report:
                write_json(args.report, result)
        elif args.command == "review":
            cases, documents, _ = load_fixtures(args.fixtures)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render_review(cases, documents), encoding="utf-8", newline="\n")
            result = {"review_file": str(args.output), "cases": len(cases)}
        else:
            selection = json.loads(
                (args.fixtures / "dataset-selection.json").read_text(encoding="utf-8")
            )
            if args.command == "freeze-fixtures":
                if (args.fixtures / "evaluation" / "manifest.json").exists():
                    raise FileExistsError("Frozen fixtures already exist; choose a new version")
                result = freeze_fixtures(
                    stream_rows(selection["revision"], "validation"), args.fixtures, selection
                )
            else:
                if args.output.exists():
                    raise FileExistsError(
                        "Output already exists; verify it or choose a new directory"
                    )
                result = prepare_bundle(
                    stream_rows(selection["revision"], "train"),
                    selection,
                    args.fixtures,
                    args.output,
                    args.count if args.count is not None else selection["target_hotpot_passages"],
                    progress=lambda rows, count: print(
                        f"Scanned {rows} rows; {count} unique passages", flush=True
                    ),
                )
        print(json.dumps(result, indent=2))
    except (ValueError, FileExistsError, FileNotFoundError) as error:
        parser.exit(1, f"Preparation error: {error}\n")


if __name__ == "__main__":
    main()
