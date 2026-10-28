"""Opt-in paid browser smoke. Start the real API and npm run preview before this command."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "backend"))
from app.config import Settings
from app.providers import UsageLedger


def main():
    config = Settings()
    token = config.demo_admin_token.get_secret_value()
    if not token:
        raise SystemExit("Configure DEMO_ADMIN_TOKEN in the server .env first.")
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required for this browser check.")
    ledger = UsageLedger(config.usage_db, config.api_budget_usd)
    before = ledger.summary()
    environment = {**os.environ, "LIVE_DEMO_ADMIN_TOKEN": token}
    # Token travels only in the child environment; it is not a command argument or report.
    completed = subprocess.run([node, "tests/live-smoke.mjs"], cwd="frontend", env=environment)
    if completed.returncode:
        raise SystemExit(completed.returncode)
    path = Path("artifacts/browser-live-verification.json")
    report = json.loads(path.read_text(encoding="utf-8"))
    report.update(usage_before=before, usage_after=ledger.summary())
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Live browser report:", path)


if __name__ == "__main__":
    main()
