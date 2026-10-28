"""Opt-in two-phase public deployment probe. Only uniquely labelled owned sources are changed."""

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import Settings
from app.evaluation.state import exclusive_run, save
from app.providers import UsageLedger
from deployment_checks import DeploymentChecks, document_etag, origin


def now():
    return datetime.now(UTC).isoformat()


def boot(probe):
    response = probe.request("GET", "/api/live")
    assert response.status_code == 200, "Public app is not live."
    instance = response.headers.get("x-investigation-instance", "")
    release = response.headers.get("x-release-revision", "")
    assert re.fullmatch(r"[a-f0-9]{32}", instance), "Missing boot identity."
    assert re.fullmatch(r"[a-f0-9]{40}", release), "Missing release identity."
    return {"instance_id": instance, "release_revision": release}


def check_result(result, state):
    """Check the known fictional fact plus all visible retrieval/citation identities."""
    updated = state["updated"]
    assert result["status"] == "answered" and "21 minutes" in result["answer"]
    hits = result["evidence"] + [
        hit for trace in result["search_trace"] for hit in trace["evidence"]
    ]
    for hit in hits:
        assert hit["document_id"] != state["deleted"]["document_id"], "Deleted source retrieved."
        if hit["document_id"] == updated["document_id"]:
            assert hit["revision_id"] == updated["revision_id"], "Inactive revision retrieved."
    by_id = {hit["evidence_id"]: hit for hit in result["evidence"]}
    citations = [citation for claim in result["claims"] for citation in claim["citations"]]
    assert any(
        by_id[c["evidence_id"]]["document_id"] == updated["document_id"]
        and by_id[c["evidence_id"]]["revision_id"] == updated["revision_id"]
        and "21 minutes" in c["quote"]
        for c in citations
    ), "The updated fact was not cited from its active source."
    for citation in citations:
        assert citation["quote"] in by_id[citation["evidence_id"]]["text"]


def assert_owned(document, state):
    assert document["document_id"] in state["owned"], "Source is not owned by this probe."
    assert document["filename"].startswith(state["marker"]), "Source filename changed."
    assert state["marker"] in document["text"], "Source ownership marker is absent."
    expected = state["owned"][document["document_id"]]
    assert document["revision_id"] == expected["revision_id"], "Source was edited externally."


class CloudCheck:
    def __init__(self, probe, ledger, path):
        self.probe, self.ledger, self.path = probe, ledger, path

    def persist(self, state):
        save(self.path, state)

    def reserve(self, state, name, amount):
        assert name not in state["spending"], "Paid step already attempted; no automatic retry."
        call = self.ledger.reserve(f"cloud:{state['marker']}:{name}", amount)
        state["spending"][name] = {"local_reservation_id": call, "reserved_usd": amount}
        self.persist(state)
        return call

    def upload(self, state, name, text):
        self.reserve(state, name, 0.001)
        response = self.probe.request(
            "POST",
            "/api/documents",
            admin=True,
            files={"file": (f"{state['marker']}-{name}.txt", text.encode(), "text/plain")},
        )
        assert response.status_code == 201, "Probe did not create a new source; not adopting it."
        document = response.json()["document"]
        # Persist ownership before readiness assertions or further mutations.
        state["owned"][document["document_id"]] = document
        self.persist(state)
        assert document["index_status"] == "ready"
        self.probe.owned.add(document["document_id"])
        return document, document_etag(response)

    def question(self, state, phase):
        call = self.reserve(state, f"question-{phase}", 0.08)
        response = self.probe.request(
            "POST",
            "/api/investigations",
            json={
                "question": "What recovery time was documented for fictional deployment case "
                + state["marker"]
                + "?"
            },
            timeout=105,
        )
        state[f"question_{phase}"] = {"http": response.status_code}
        if response.status_code == 200:
            result = response.json()
            state[f"question_{phase}"]["result"] = result
            usage = result["usage"]
            rows = (
                usage["planning"]
                + [usage["generation"], usage.get("verification")]
                + usage["embeddings"]
            )
            rows = [row for row in rows if row]
            self.ledger.complete(
                call,
                sum(row.get("input_tokens", 0) for row in rows),
                sum(row.get("output_tokens", 0) for row in rows),
                usage["estimated_total_cost_usd"],
            )
        self.persist(state)
        assert response.status_code == 200, "Paid investigation failed; receipt retained."
        check_result(result, state)

    def prepare(self):
        assert not self.path.exists(), (
            "State exists; use verify/cleanup or choose a new state path."
        )
        state = {
            "url": self.probe.base,
            "marker": "CLOUD-" + uuid4().hex,
            "started_at": now(),
            "before": boot(self.probe),
            "owned": {},
            "spending": {},
            "phase": "preparing",
            "passed": False,
            "ledger_before": self.ledger.summary(),
        }
        self.persist(state)
        surface = self.probe.probe_public()
        surface["health"] = {"status": surface["health"]["status"]}
        state["surface_before"] = surface
        text = f"Fictional deployment case {state['marker']}. The documented recovery time was "
        first, etag = self.upload(state, "updated", text + "13 minutes.")
        deleted, delete_etag = self.upload(state, "deleted", text + "97 minutes.")
        state["deleted"] = deleted
        self.reserve(state, "replacement", 0.001)
        first, active_etag = self.probe.replace(
            first["document_id"], etag, text + "21 minutes.", f"{state['marker']}-updated.txt"
        )
        state["owned"][first["document_id"]] = first
        state.update(updated=first, updated_etag=active_etag, updated_text=text + "21 minutes.")
        self.persist(state)
        stale = self.probe.request(
            "DELETE",
            f"/api/documents/{first['document_id']}",
            admin=True,
            headers={"If-Match": etag},
        )
        assert stale.status_code == 412, "Stale ETag was not rejected."
        state["stale_etag_http"] = stale.status_code
        self.probe.remove(deleted["document_id"], delete_etag)
        assert self.probe.read(deleted["document_id"]).status_code == 404
        self.question(state, "before")
        assert boot(self.probe) == state["before"], "App restarted during preparation."
        state.update(phase="prepared", prepared_at=now(), ledger_after=self.ledger.summary())
        self.persist(state)
        return state

    def load(self):
        state = json.loads(self.path.read_text(encoding="utf-8"))
        assert state["url"] == self.probe.base, "State belongs to a different public origin."
        assert re.fullmatch(r"CLOUD-[a-f0-9]{32}", state["marker"]), "Invalid ownership marker."
        return state

    def cleanup(self, state):
        for identifier in state["owned"]:
            response = self.probe.read(identifier)
            if response.status_code == 404:
                continue
            assert response.status_code == 200, "Cannot safely inspect owned source."
            assert_owned(response.json(), state)
            self.probe.owned.add(identifier)
            self.probe.remove(identifier, document_etag(response))
            assert self.probe.read(identifier).status_code == 404
        state["cleanup_completed_at"] = now()
        self.persist(state)

    def verify(self, expected_revision):
        state = self.load()
        assert state["phase"] == "prepared", "Complete preparation before checking a restart."
        after = boot(self.probe)
        assert after["instance_id"] != state["before"]["instance_id"], "No actual restart observed."
        if expected_revision:
            assert after["release_revision"] == expected_revision, "Expected release is not live."
        state["after"] = after
        surface = self.probe.probe_public()
        surface["health"] = {"status": surface["health"]["status"]}
        state["surface_after"] = surface
        updated = self.probe.read(state["updated"]["document_id"])
        assert updated.status_code == 200
        assert_owned(updated.json(), state)
        assert updated.json()["text"] == state["updated_text"]
        assert document_etag(updated) == state["updated_etag"]
        assert self.probe.read(state["deleted"]["document_id"]).status_code == 404
        state["persisted"] = {"text": True, "revision": True, "etag": True, "deletion": True}
        self.persist(state)
        self.question(state, "after")
        assert boot(self.probe) == after, "App restarted during verification."
        self.cleanup(state)
        state.update(
            phase="verified", passed=True, finished_at=now(), ledger_after=self.ledger.summary()
        )
        self.persist(state)
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "verify", "cleanup"))
    parser.add_argument("--url", required=True, type=origin)
    parser.add_argument(
        "--state", type=Path, default=Path("artifacts/cloud-persistence/state.json")
    )
    parser.add_argument("--expected-revision")
    args = parser.parse_args()
    config = Settings()
    token = config.demo_admin_token.get_secret_value()
    assert token, "Configure the demo admin token locally; never pass secrets on the command line."
    ledger = UsageLedger(config.usage_db, config.api_budget_usd)
    with (
        exclusive_run(args.state.parent),
        httpx.Client(timeout=60, follow_redirects=False) as client,
    ):
        probe = DeploymentChecks(
            client,
            args.url,
            token,
            secrets=(
                config.openai_api_key.get_secret_value(),
                config.qdrant_api_key.get_secret_value(),
            ),
        )
        check = CloudCheck(probe, ledger, args.state)
        if args.phase == "prepare":
            state = check.prepare()
        elif args.phase == "verify":
            state = check.verify(args.expected_revision)
        else:
            state = check.load()
            check.cleanup(state)
        print(
            json.dumps({"phase": args.phase, "passed": state["passed"], "state": str(args.state)})
        )


if __name__ == "__main__":
    main()
