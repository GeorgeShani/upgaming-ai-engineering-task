import secrets

from starlette.responses import JSONResponse

from .parsing import MAX_UPLOAD_BYTES

MAX_REQUEST_BYTES = MAX_UPLOAD_BYTES + 65_536


class DocumentMutationBoundary:
    """Authenticate before multipart parsing, then bound the entire incoming request."""

    def __init__(self, app, settings):
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        guarded = path == "/api/documents" or path.startswith("/api/documents/")
        if (
            scope["type"] != "http"
            or not guarded
            or scope["method"] not in {"POST", "PUT", "DELETE"}
        ):
            return await self.app(scope, receive, send)
        settings = self.settings()
        expected = settings.demo_admin_token.get_secret_value().encode("utf-8")
        headers = dict(scope["headers"])
        supplied = headers.get(b"authorization", b"")
        if not expected:
            return await JSONResponse(
                {"detail": "Set DEMO_ADMIN_TOKEN on the server to enable mutations."}, 503
            )(scope, receive, send)
        if not supplied[:7].lower() == b"bearer " or not secrets.compare_digest(
            supplied[7:], expected
        ):
            return await JSONResponse(
                {"detail": "A valid demo admin bearer token is required."},
                401,
                headers={"WWW-Authenticate": "Bearer"},
            )(scope, receive, send)
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) < 0 or int(content_length) > MAX_REQUEST_BYTES:
                    return await self.reject_size(scope, receive, send)
            except ValueError:
                return await JSONResponse({"detail": "Invalid Content-Length."}, 400)(
                    scope, receive, send
                )
        parts, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            data = message.get("body", b"")
            size += len(data)
            if size > MAX_REQUEST_BYTES:
                return await self.reject_size(scope, receive, send)
            parts.append(data)
            if not message.get("more_body", False):
                break
        body = b"".join(parts)
        consumed = False

        async def bounded_receive():
            nonlocal consumed
            if consumed:
                return await receive()
            consumed = True
            return {"type": "http.request", "body": body, "more_body": False}

        await self.app(scope, bounded_receive, send)

    async def reject_size(self, scope, receive, send):
        await JSONResponse(
            {"detail": "Request exceeds the 5 MB file plus multipart overhead limit."}, 413
        )(scope, receive, send)
