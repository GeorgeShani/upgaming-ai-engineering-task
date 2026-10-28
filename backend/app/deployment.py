"""Opaque boot identity and public commit metadata for restart verification."""

import os
import re
from uuid import uuid4


class DeploymentIdentity:
    def __init__(self, app):
        self.app = app
        self.instance = uuid4().hex.encode("ascii")
        revision = os.environ.get("RENDER_GIT_COMMIT", os.environ.get("APP_REVISION", ""))
        self.revision = (
            revision if re.fullmatch(r"[a-fA-F0-9]{40}", revision) else "unknown"
        ).encode("ascii")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def with_identity(message):
            if message["type"] == "http.response.start":
                message = {
                    **message,
                    "headers": [
                        *message.get("headers", []),
                        (b"x-investigation-instance", self.instance),
                        (b"x-release-revision", self.revision),
                    ],
                }
            await send(message)

        await self.app(scope, receive, with_identity)
