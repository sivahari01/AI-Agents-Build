"""Pydantic models shared by parsers, integrations, and analysis modules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    value: float | None = None
    metric: str
    unit: str | None = None
    source: str
    attributes: dict[str, Any] = Field(default_factory=dict)


class TransactionMetric(BaseModel):
    name: str
    execution_count: int | None = None
    average_response_time_s: float | None = None
    min_response_time_s: float | None = None
    max_response_time_s: float | None = None
    p90_response_time_s: float | None = None
    p95_response_time_s: float | None = None
    p99_response_time_s: float | None = None
    error_count: int | None = None
    error_pct: float | None = None


class PerformanceReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    source_type: str
    source_name: str
    scenario_name: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    peak_vus: float | None = None
    total_requests: int | None = None
    successful_requests: int | None = None
    failed_requests: int | None = None
    error_rate_pct: float | None = None
    average_response_time_s: float | None = None
    p90_response_time_s: float | None = None
    p95_response_time_s: float | None = None
    p99_response_time_s: float | None = None
    transaction_tps: float | None = None
    request_rps: float | None = None
    iteration_ips: float | None = None
    transactions: list[TransactionMetric] = Field(default_factory=list)
    time_series: list[TimeSeriesPoint] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    category: str
    severity: str
    title: str
    observation: str
    evidence: list[str] = Field(default_factory=list)
    hypothesis: str | None = None
    confidence: str = "low"
    time_window: str | None = None
    recommendation: str | None = None
