"""HTTP-level fake: exercises the real store without a paid service or Qdrant process."""

import json

import httpx


class FakeQdrant:
    def __init__(self):
        self.collections = {}
        self.indexes = {}
        self.fail_next = None

    def __call__(self, request):
        path = request.url.path.split("/")
        collection = path[2]
        body = json.loads(request.content) if request.content else None
        suffix = "/".join(path[3:])
        if not suffix:
            if request.method == "PUT":
                assert body == {"vectors": {}}
                self.collections[collection] = {}
                self.indexes[collection] = set()
                return httpx.Response(200, json={"result": True})
            if collection in self.collections:
                return httpx.Response(200, json={"result": {"status": "green"}})
        if collection not in self.collections:
            return httpx.Response(404, json={"status": "not found"})
        if suffix == "index":
            self.indexes[collection].add(body["field_name"])
            return httpx.Response(200, json={"result": {"status": "completed"}})
        points = self.collections[collection]
        if suffix == "points" and request.method == "PUT":
            point = body["points"][0]
            assert point["vector"] == {}
            phase = "revision" if collection.endswith("revisions_v1") else "manifest"
            if self.fail_next == phase:
                self.fail_next = None
                return httpx.Response(500, text="private-provider-details")
            points[point["id"]] = point["payload"]
            if self.fail_next == "after_manifest" and phase == "manifest":
                self.fail_next = None
                raise httpx.ReadTimeout("private-provider-details", request=request)
            return httpx.Response(200, json={"result": {"status": "completed"}})
        if suffix == "points":
            return httpx.Response(
                200,
                json={
                    "result": [
                        {"id": key, "payload": points[key]} for key in body["ids"] if key in points
                    ]
                },
            )
        if suffix == "points/scroll":
            conditions = body["filter"]["must"]
            assert all(c["key"] in self.indexes[collection] for c in conditions)
            rows = [
                {"id": key, "payload": value}
                for key, value in sorted(points.items())
                if all(value.get(c["key"]) == c["match"]["value"] for c in conditions)
                and (not body.get("offset") or key >= body["offset"])
            ]
            limit = body["limit"]
            return httpx.Response(
                200,
                json={
                    "result": {
                        "points": rows[:limit],
                        "next_page_offset": rows[limit]["id"] if len(rows) > limit else None,
                    }
                },
            )
        raise AssertionError(f"Unexpected Qdrant route: {request.method} {suffix}")
