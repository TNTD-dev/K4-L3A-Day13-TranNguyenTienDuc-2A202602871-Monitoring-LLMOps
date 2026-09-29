from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.dashboard_data import dashboard_snapshot


def test_dashboard_aggregates_all_six_panels_from_log_events(tmp_path: Path) -> None:
    now = datetime(2026, 9, 29, 8, 0, tzinfo=timezone.utc)
    stamp = (now - timedelta(minutes=2)).isoformat()
    records = [
        {"ts": stamp, "event": "request_received"},
        {"ts": stamp, "event": "response_sent", "latency_ms": 1200, "ttft_ms": 80, "cost_usd": 0.003, "tokens_in": 100, "tokens_out": 150, "quality_score": 0.8, "tool_success": True},
        {"ts": stamp, "event": "request_received"},
        {"ts": stamp, "event": "request_failed", "error_type": "RuntimeError", "tool_success": False},
        {"ts": (now - timedelta(hours=2)).isoformat(), "event": "request_received"},
    ]
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text("\n".join(json.dumps(record) for record in records) + "\nnot json\n", encoding="utf-8")

    snapshot = dashboard_snapshot(log_path, now=now)
    summary = snapshot["summary"]
    assert summary["latency_p95_ms"] == 1200
    assert summary["ttft_p95_ms"] == 80
    assert summary["request_count"] == 2
    assert summary["error_rate_pct"] == 50
    assert summary["retrieval_success_pct"] == 50
    assert summary["error_breakdown"] == {"RuntimeError": 1}
    assert summary["cost_total_usd"] == 0.003
    assert summary["tokens_in"] == 100 and summary["tokens_out"] == 150
    assert summary["quality_mean"] == 0.8


def test_dashboard_handles_missing_log_without_inventing_data(tmp_path: Path) -> None:
    snapshot = dashboard_snapshot(tmp_path / "missing.jsonl")
    assert snapshot["summary"]["request_count"] == 0
    assert snapshot["summary"]["latency_p95_ms"] is None
    assert snapshot["summary"]["error_rate_pct"] is None
