"""Aggregate the application's JSONL log contract for the six-panel dashboard."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any


def percentile(values: list[float], percent: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * percent / 100) - 1)], 2)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def dashboard_snapshot(
    log_path: Path, *, now: datetime | None = None, window_minutes: int = 60
) -> dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = now - timedelta(minutes=window_minutes)
    rows: list[tuple[datetime, dict[str, Any]]] = []
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
                timestamp = datetime.fromisoformat(record["ts"].replace("Z", "+00:00"))
                timestamp = timestamp.astimezone(timezone.utc)
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
            if start <= timestamp <= now and isinstance(record, dict):
                rows.append((timestamp, record))

    requests = [record for _, record in rows if record.get("event") == "request_received"]
    failures = [record for _, record in rows if record.get("event") == "request_failed"]
    responses = [record for _, record in rows if record.get("event") == "response_sent"]
    latencies = [value for record in responses if (value := _number(record.get("latency_ms"))) is not None]
    ttfts = [value for record in responses if (value := _number(record.get("ttft_ms"))) is not None]
    costs = [value for record in responses if (value := _number(record.get("cost_usd"))) is not None]
    qualities = [value for record in responses if (value := _number(record.get("quality_score"))) is not None]
    outcomes = [
        record["tool_success"]
        for record in responses + failures
        if isinstance(record.get("tool_success"), bool)
    ]
    breakdown = Counter(str(record.get("error_type") or "Unknown") for record in failures)

    minute_start = start.replace(second=0, microsecond=0)
    buckets: dict[datetime, dict[str, Any]] = defaultdict(
        lambda: {"requests": 0, "errors": 0, "latencies": [], "cost": 0.0, "tokens_in": 0, "tokens_out": 0, "qualities": []}
    )
    for timestamp, record in rows:
        bucket = buckets[timestamp.replace(second=0, microsecond=0)]
        event = record.get("event")
        if event == "request_received":
            bucket["requests"] += 1
        elif event == "request_failed":
            bucket["errors"] += 1
        elif event == "response_sent":
            if (value := _number(record.get("latency_ms"))) is not None:
                bucket["latencies"].append(value)
            if (value := _number(record.get("cost_usd"))) is not None:
                bucket["cost"] += value
            for field in ("tokens_in", "tokens_out"):
                if (value := _number(record.get(field))) is not None:
                    bucket[field] += int(value)
            if (value := _number(record.get("quality_score"))) is not None:
                bucket["qualities"].append(value)

    minutes = [minute_start + timedelta(minutes=index) for index in range(window_minutes + 1)]
    timeline = [buckets[minute] for minute in minutes]
    total_cost = sum(costs)
    return {
        "window": {"minutes": window_minutes, "start": start.isoformat(), "end": now.isoformat(), "refresh_seconds": 30},
        "summary": {
            "latency_p50_ms": percentile(latencies, 50),
            "latency_p95_ms": percentile(latencies, 95),
            "latency_p99_ms": percentile(latencies, 99),
            "ttft_p95_ms": percentile(ttfts, 95),
            "request_count": len(requests),
            "request_rate_per_minute": round(len(requests) / window_minutes, 2),
            "error_rate_pct": round(len(failures) / len(requests) * 100, 2) if requests else None,
            "error_breakdown": dict(breakdown),
            "retrieval_success_pct": round(sum(outcomes) / len(outcomes) * 100, 2) if outcomes else None,
            "cost_total_usd": round(total_cost, 6),
            "cost_per_request_usd": round(total_cost / len(responses), 6) if responses else None,
            "tokens_in": sum(int(_number(record.get("tokens_in")) or 0) for record in responses),
            "tokens_out": sum(int(_number(record.get("tokens_out")) or 0) for record in responses),
            "quality_mean": round(mean(qualities), 3) if qualities else None,
        },
        "series": {
            "labels": [minute.isoformat() for minute in minutes],
            "latency_p95_ms": [percentile(bucket["latencies"], 95) for bucket in timeline],
            "traffic": [bucket["requests"] for bucket in timeline],
            "errors": [bucket["errors"] for bucket in timeline],
            "error_rate_pct": [
                round(bucket["errors"] / bucket["requests"] * 100, 2)
                if bucket["requests"] else None for bucket in timeline
            ],
            "cost_usd": [round(bucket["cost"], 6) for bucket in timeline],
            "tokens_in": [bucket["tokens_in"] for bucket in timeline],
            "tokens_out": [bucket["tokens_out"] for bucket in timeline],
            "quality": [round(mean(bucket["qualities"]), 3) if bucket["qualities"] else None for bucket in timeline],
        },
    }
