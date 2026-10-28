"""Atomic receipts and an OS-released SQLite lock make paid batches resumable."""

import json
import sqlite3
from contextlib import closing, contextmanager


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    temporary.replace(path)


def load_or_create(path, value):
    if path.exists():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous["identity"] != value["identity"]:
            raise ValueError("Evaluation identity changed; use a new output directory.")
        return previous
    save(path, value)
    return value


@contextmanager
def exclusive_run(folder):
    folder.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(folder / ".run-lock.sqlite3", timeout=0)) as db:
        try:
            db.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError as error:
            raise ValueError("Another evaluation is running in this output directory.") from error
        try:
            yield
        finally:
            db.rollback()


def recover_pending(folder, ledger):
    recovered = []
    for pending in sorted(folder.glob("*.pending.json")):
        target = pending.with_name(pending.name.removesuffix(".pending.json") + ".json")
        if not target.exists():
            record = json.loads(pending.read_text(encoding="utf-8"))
            record.update(error="interrupted_uncertain", result=None, ledger_after=ledger)
            save(target, record)
            recovered.append(record)
        pending.unlink()
    return recovered


def attempt_order(case_ids):
    return [
        (key, strategy)
        for i, key in enumerate(case_ids)
        for strategy in (("a", "b") if i % 2 == 0 else ("b", "a"))
    ]
