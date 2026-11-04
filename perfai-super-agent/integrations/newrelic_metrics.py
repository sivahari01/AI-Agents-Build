"""Candidate New Relic metric queries. Names are used only when discovered."""
from __future__ import annotations
from datetime import datetime, timezone

CANDIDATE_METRICS = {
    "cpu": ["cpuPercent", "host.cpuPercent", "system.cpu.utilization"],
    "memory": ["memoryUsedPercent", "host.memoryUsedPercent", "system.memory.utilization"],
    "apm_duration": ["apm.service.transaction.duration"],
    "apm_throughput": ["apm.service.transaction.throughput"],
    "apm_errors": ["apm.service.error.count"],
    "jvm_heap": ["jvm.memory.heap.used", "jvm.memory.heap.max"],
    "gc": ["jvm.gc.duration", "jvm.gc.pause"],
}

def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "''")

def build_metric_queries(entity_guid: str, discovered_keys: set[str],
                         since: str = "60 minutes ago") -> list[dict]:
    guid = _escape(entity_guid)
    queries = []
    for group, candidates in CANDIDATE_METRICS.items():
        for key in candidates:
            if key in discovered_keys:
                queries.append({"group": group, "metric_key": key,
                    "nrql": f"FROM Metric SELECT average(value) AS value WHERE entity.guid = '{guid}' AND metricName = '{_escape(key)}' TIMESERIES 1 minute SINCE {since}"})
    return queries

def results_to_points(results: list[dict], metric_key: str) -> list[dict]:
    points = []
    for row in results:
        raw = row.get("beginTimeSeconds", row.get("timestamp"))
        if raw is None:
            continue
        try:
            if isinstance(raw, (int, float)):
                stamp = datetime.fromtimestamp(raw, tz=timezone.utc)
            else:
                stamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                stamp = stamp.replace(tzinfo=stamp.tzinfo or timezone.utc).astimezone(timezone.utc)
        except (ValueError, OverflowError, OSError):
            continue
        value = row.get("value", row.get("average.value", row.get("average")))
        try:
            value = float(value) if value is not None else None
        except (TypeError, ValueError):
            value = None
        points.append({"timestamp": stamp, "value": value, "metric": metric_key,
                       "unit": None, "source": "New Relic"})
    return points
