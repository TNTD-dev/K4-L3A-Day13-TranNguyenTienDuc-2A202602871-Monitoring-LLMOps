from __future__ import annotations

import asyncio
import json
import re
from contextlib import contextmanager
from pathlib import Path

import httpx

from app import agent as agent_module, logging_config
from app.main import app


def test_concurrent_requests_keep_distinct_ids_and_scrub_pii(monkeypatch, tmp_path: Path) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def run_requests():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            payload = lambda user: {"user_id": user, "session_id": "0901234567", "feature": "qa", "message": "Email student@example.com about monitoring"}
            return await asyncio.gather(
                client.post("/chat", json=payload("student-1"), headers={"x-request-id": "req-ABCDEF12"}),
                client.post("/chat", json=payload("student-2"), headers={"x-request-id": "not-valid"}),
            )

    first, second = asyncio.run(run_requests())
    assert first.status_code == second.status_code == 200
    assert first.headers["x-request-id"] == "req-abcdef12"
    assert re.fullmatch(r"req-[0-9a-f]{8}", second.headers["x-request-id"])
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
    assert float(first.headers["x-response-time-ms"]) >= 0
    logs = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    received = [line for line in logs if line["event"] == "request_received"]
    assert {line["correlation_id"] for line in received} == {first.headers["x-request-id"], second.headers["x-request-id"]}
    assert len({line["user_id_hash"] for line in received}) == 2
    assert all({"session_id", "feature", "model", "env"} <= line.keys() for line in received)
    assert "student@example.com" not in log_path.read_text(encoding="utf-8")
    assert "0901234567" not in log_path.read_text(encoding="utf-8")


def test_agent_creates_child_retrieval_and_generation_without_raw_io(monkeypatch) -> None:
    class Observation:
        def __init__(self):
            self.updates = []

        def update(self, **kwargs):
            self.updates.append(kwargs)

    class Client:
        def __init__(self):
            self.children = []

        @contextmanager
        def start_as_current_observation(self, **kwargs):
            observation = Observation()
            self.children.append((kwargs, observation))
            yield observation

        def update_current_span(self, **kwargs):
            pass

    client = Client()
    monkeypatch.setattr(agent_module, "get_langfuse_client", lambda: client)
    monkeypatch.setattr(agent_module, "tracing_enabled", lambda: False)
    @contextmanager
    def attributes(**kwargs):
        yield
    monkeypatch.setattr(agent_module, "propagate_attributes", attributes)
    agent_module.LabAgent.run.__wrapped__(
        agent_module.LabAgent(), "student-1", "qa", "session-1", "Explain monitoring", "req-12345678"
    )
    retrieval, generation = client.children
    assert retrieval[0]["as_type"] == "retriever"
    assert generation[0]["as_type"] == "generation"
    assert generation[0]["model"] == "claude-sonnet-4-5"
    assert generation[0]["metadata"]["correlation_id"] == "req-12345678"
    assert "input" not in generation[0] and "output" not in generation[0]
    assert generation[1].updates[0]["usage_details"]["input"] > 0
    assert generation[1].updates[0]["cost_details"]["total"] > 0
