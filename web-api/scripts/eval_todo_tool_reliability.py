"""Manual reliability eval for Genie's todo tool-calling against the live Ollama model.

The automated integration suite (tests/integration/test_chat_todo_tools.py) mocks the
Ollama client, so it verifies prompt/routing logic deterministically but can't measure
the probabilistic failure mode where the live model skips calling a tool and just
narrates a false success in free text (e.g. "好的，我已經為您新增了..." with nothing
actually created). This script measures that failure rate directly, by checking actual
API/DB state after each trial rather than trusting the assistant's reply text — so it can
be re-run before/after a temperature or prompt change to see whether the change helped.

Not wired into CI: needs a live Ollama server and a running scratch backend.

Usage (with the scratch stack up per CLAUDE.md's "Manual/ad-hoc verification" section):
    uv run python scripts/eval_todo_tool_reliability.py --trials 20
    uv run python scripts/eval_todo_tool_reliability.py --trials 20 --base-url http://localhost:8090
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

import httpx

WEB_API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WEB_API_ROOT))

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "SCRATCH_DATABASE_URL",
        "postgresql+psycopg://living_genie:living_genie@localhost:5432/living_genie_scratch",
    ),
)

# Only safe to import app.* below this point: app.db creates the SQLAlchemy engine and
# app.main creates the uploads dir at import time, both from the env var set above.
from datetime import datetime, timezone  # noqa: E402

from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402

CREATE_TODO_PHRASINGS = [
    "新增一筆待辦事項，內容是{marker}",
    "幫我加一個待辦：{marker}",
    "Add a todo: {marker}",
    "請新增待辦事項「{marker}」",
]


def _provision_verified_user(email: str, password: str) -> None:
    """Creates (or resets) a scratch user and marks it verified directly via the DB,
    bypassing the email-verification flow — this script only runs against the scratch
    database, never the developer's real one (see CLAUDE.md).
    """
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, hashed_password=hash_password(password))
            db.add(user)
        else:
            user.hashed_password = hash_password(password)
        user.email_verified_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def _login(client: httpx.Client, email: str, password: str) -> None:
    resp = client.post("/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()


def _new_conversation(client: httpx.Client) -> str:
    resp = client.post("/conversations", json={})
    resp.raise_for_status()
    return resp.json()["id"]


def _send_message(client: httpx.Client, conversation_id: str, content: str) -> str:
    """Sends a chat message and returns the concatenated assistant reply text."""
    with client.stream(
        "POST", f"/conversations/{conversation_id}/messages", json={"content": content}
    ) as resp:
        resp.raise_for_status()
        text = ""
        for line in resp.iter_lines():
            if line.startswith("data:"):
                payload = json.loads(line[len("data:") :])
                if "text" in payload:
                    text += payload["text"]
        return text


def _todo_titles(client: httpx.Client) -> set[str]:
    resp = client.get("/todos")
    resp.raise_for_status()
    return {todo["title"] for todo in resp.json()}


def run_create_todo_trials(client: httpx.Client, trials: int) -> None:
    successes = 0
    false_claims = 0
    for i in range(trials):
        marker = f"eval-marker-{uuid.uuid4().hex[:8]}"
        phrasing = CREATE_TODO_PHRASINGS[i % len(CREATE_TODO_PHRASINGS)]
        message = phrasing.format(marker=marker)

        before = _todo_titles(client)
        conversation_id = _new_conversation(client)
        reply = _send_message(client, conversation_id, message)
        after = _todo_titles(client)

        created = any(marker in title for title in after - before)
        claimed_success = marker in reply or any(
            word in reply for word in ("已經", "已新增", "added", "created")
        )

        status = "OK  " if created else "MISS"
        note = ""
        if not created and claimed_success:
            false_claims += 1
            note = "  <-- claimed success but nothing was created"
        print(f"[{i + 1:>2}/{trials}] {status} message={message!r}{note}")

        if created:
            successes += 1

    print()
    print(f"Tool actually invoked: {successes}/{trials} ({successes / trials:.0%})")
    print(f"False success claims (no tool call, but reply implied one): {false_claims}/{trials}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8090")
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--email", default="eval-todo-reliability@example.com")
    parser.add_argument("--password", default="EvalPass123!")
    args = parser.parse_args()

    _provision_verified_user(args.email, args.password)

    with httpx.Client(base_url=args.base_url, timeout=60.0) as client:
        _login(client, args.email, args.password)
        run_create_todo_trials(client, args.trials)


if __name__ == "__main__":
    main()
