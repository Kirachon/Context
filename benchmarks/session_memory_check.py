from __future__ import annotations

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.ai_processing.conversation_tracker import get_conversation_tracker
from src.ai_processing.session_manager import get_session_manager
from src.ai_processing.session_manager import get_session_manager


def approx_bytes_of_messages(history) -> int:
    # Rough approximation focusing on content strings
    total = 0
    for m in history:
        total += len(m.get("role", ""))
        total += len(m.get("content", ""))
    return total


def run(num_sessions: int = 200, msgs_per_session: int = 50, content_len: int = 200) -> dict:
    sm = get_session_manager()
    ct = get_conversation_tracker()

    # Create sessions and populate messages
    for _ in range(num_sessions):
        sid = sm.create()
        for i in range(msgs_per_session):
            ct.add(sid, "user" if i % 2 == 0 else "assistant", "x" * content_len)

    # Approximate memory by summing string lengths
    approx_bytes = 0
    for sid in list(sm._sessions):  # access internal set for demo purpose
        approx_bytes += approx_bytes_of_messages(ct.history(sid))

    approx_mb = approx_bytes / (1024 * 1024)
    return {
        "sessions": num_sessions,
        "msgs_per_session": msgs_per_session,
        "content_len": content_len,
        "approx_mb": round(approx_mb, 2),
        "threshold_mb": 100.0,
        "ok": approx_mb < 100.0,
    }


if __name__ == "__main__":
    result = run()
    print(result)

