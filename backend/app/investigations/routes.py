import time
from collections import deque

from fastapi import APIRouter, HTTPException, Request

from .models import Question

router = APIRouter(prefix="/api/investigations", tags=["Investigations"])


class DemoRateLimit:
    """One-process global limit: visitors share six requests per minute."""

    def __init__(self):
        self.accepted = deque()

    def check(self):
        now = time.monotonic()
        while self.accepted and self.accepted[0] <= now - 60:
            self.accepted.popleft()
        if len(self.accepted) >= 6:
            raise HTTPException(
                429, "Demo limit: six investigations per minute.", headers={"Retry-After": "60"}
            )
        self.accepted.append(now)


@router.post("")
async def investigate(body: Question, request: Request):
    manager = request.app.state.investigation_service
    if manager is None:
        raise HTTPException(503, "Configure both OpenAI and Qdrant before investigating.")
    question = body.question.strip()
    if len(question) < 3:
        raise HTTPException(422, "Enter a non-empty question of at least three characters.")
    request.app.state.investigation_rate_limit.check()
    # Do not build an unbounded queue of paid work on a small free service.
    slots = request.app.state.investigation_slots
    if slots.locked():
        raise HTTPException(
            429,
            "An investigation is already running. Try again shortly.",
            headers={"Retry-After": "5"},
        )
    async with slots:
        return await manager.bounded_investigate(
            question,
            body.strategy or request.app.state.settings.retrieval_strategy,
        )
