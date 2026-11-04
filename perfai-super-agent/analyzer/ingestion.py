"""Load-test report ingestion and normalization."""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup

from models import PerformanceReport, TimeSeriesPoint, TransactionMetric


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def _time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = pd.to_datetime(value, utc=True)
        return parsed.to_pydatetime()
    except (TypeError, ValueError):
        return None


def _first(mapping: dict, *keys: str):
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _transaction_rows(rows: list[dict]) -> list[TransactionMetric]:
    output = []
    for row in rows:
        name = _first(row, "name", "transaction", "label", "Transaction", "Label")
        if not name:
            continue
        output.append(TransactionMetric(
            name=str(name),
            execution_count=int(_number(_first(row, "execution_count", "count", "samples", "Executions")) or 0),
            average_response_time_s=_seconds(_first(row, "average_response_time_s", "avg_response_time_s", "avg", "Average")),
            min_response_time_s=_seconds(_first(row, "min_response_time_s", "min")),
            max_response_time_s=_seconds(_first(row, "max_response_time_s", "max")),
            p90_response_time_s=_seconds(_first(row, "p90_response_time_s", "p90", "pct1")),
            p95_response_time_s=_seconds(_first(row, "p95_response_time_s", "p95", "pct2")),
            p99_response_time_s=_seconds(_first(row, "p99_response_time_s", "p99")),
            error_count=int(_number(_first(row, "error_count", "errors", "Error Count")) or 0),
            error_pct=_number(_first(row, "error_pct", "error_rate_pct", "Error %")),
        ))
    return output


def _seconds(value: Any) -> float | None:
    number = _number(value)
    if number is None:
        return None
    # JMeter and many CSV exports express elapsed time in milliseconds.
    return number / 1000.0 if number > 100 else number


def _timeseries(rows: list[dict], source: str) -> list[TimeSeriesPoint]:
    output = []
    for row in rows:
        stamp = _time(_first(row, "timestamp", "timeStamp", "time", "Time", "Datetime"))
        if not stamp:
            continue
        for key, unit in [
            ("response_time_s", "s"), ("response_time", "ms"),
            ("avg_response_time_s", "s"), ("throughput", "req/s"),
            ("tps", "txn/s"), ("rps", "req/s"), ("vus", "users"),
            ("users", "users"), ("error_pct", "%"), ("cpu_pct", "%"),
            ("memory_pct", "%"),
        ]:
            value = _number(row.get(key))
            if value is not None:
                if key == "response_time":
                    value /= 1000
                    metric = "response_time_s"
                else:
                    metric = key
                output.append(TimeSeriesPoint(
                    timestamp=stamp, value=value, metric=metric, unit=unit, source=source
                ))
    return output


def _normalize(payload: dict, source_type: str, source_name: str,
               transactions: list[dict] | None = None,
               points: list[TimeSeriesPoint] | None = None) -> PerformanceReport:
    txns = _transaction_rows(transactions or payload.get("transactions", []))
    start = _time(_first(payload, "started_at", "start_time", "startTime", "start"))
    end = _time(_first(payload, "ended_at", "end_time", "endTime", "end"))
    duration = _number(_first(payload, "duration_seconds", "duration", "elapsed_seconds"))
    if duration is None and start and end:
        duration = (end - start).total_seconds()
    request_count = _first(payload, "total_requests", "requests", "sample_count", "totalSamples")
    failed = _first(payload, "failed_requests", "failed", "error_count", "errors")
    if failed is None and txns:
        known_errors = [item.error_count for item in txns if item.error_count is not None]
        failed = sum(known_errors) if known_errors else None
    total = int(_number(request_count)) if _number(request_count) is not None else None
    failed_count = int(_number(failed)) if _number(failed) is not None else None
    err_pct = _number(_first(payload, "error_rate_pct", "error_pct", "error_rate"))
    if err_pct is None and total and failed_count is not None:
        err_pct = failed_count / total * 100
    return PerformanceReport(
        source_type=source_type, source_name=source_name,
        scenario_name=_first(payload, "scenario_name", "scenario", "test_name", "label"),
        started_at=start, ended_at=end, duration_seconds=duration,
        peak_vus=_number(_first(payload, "peak_vus", "max_virtual_users", "users", "threads")),
        total_requests=total,
        successful_requests=(total - failed_count) if total is not None and failed_count is not None else None,
        failed_requests=failed_count, error_rate_pct=err_pct,
        average_response_time_s=_seconds(_first(payload, "average_response_time_s", "avg_response_time_s", "average_response_time")),
        p90_response_time_s=_seconds(_first(payload, "p90_response_time_s", "p90")),
        p95_response_time_s=_seconds(_first(payload, "p95_response_time_s", "p95")),
        p99_response_time_s=_seconds(_first(payload, "p99_response_time_s", "p99")),
        transaction_tps=_number(_first(payload, "transaction_tps", "average_tps", "tps")),
        request_rps=_number(_first(payload, "request_rps", "average_requests_per_second", "rps")),
        iteration_ips=_number(_first(payload, "iteration_ips", "iterations_per_second", "ips")),
        transactions=txns, time_series=points or [],
        warnings=list(payload.get("warnings", [])),
    )


def parse_json_report(data: bytes, filename: str) -> PerformanceReport:
    payload = json.loads(data.decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("JSON report must contain an object at the root")
    ts_rows = payload.get("time_series", payload.get("timeseries", []))
    return _normalize(payload, "JSON", filename, points=_timeseries(ts_rows, filename))


def parse_csv_report(data: bytes, filename: str) -> PerformanceReport:
    text = data.decode("utf-8-sig", errors="replace")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("CSV file contains no data rows or header")
    first = rows[0]
    # JMeter CSV: timestamp, elapsed, label, responseCode, success, ...
    if "elapsed" in first and "label" in first:
        counts: dict[str, list[float]] = {}
        errors: dict[str, int] = {}
        for row in rows:
            label = row.get("label") or "Unknown"
            elapsed = _number(row.get("elapsed"))
            if elapsed is not None:
                counts.setdefault(label, []).append(elapsed / 1000)
            if str(row.get("success", "true")).lower() in {"false", "0", "no"}:
                errors[label] = errors.get(label, 0) + 1
        txns = []
        for label, samples in counts.items():
            ordered = sorted(samples)
            quantile = lambda q: ordered[min(len(ordered)-1, int((len(ordered)-1)*q))]
            txns.append({
                "name": label, "execution_count": len(samples),
                "average_response_time_s": sum(samples)/len(samples),
                "min_response_time_s": min(samples), "max_response_time_s": max(samples),
                "p90_response_time_s": quantile(.90), "p95_response_time_s": quantile(.95),
                "p99_response_time_s": quantile(.99), "error_count": errors.get(label, 0),
                "error_pct": errors.get(label, 0)/len(samples)*100,
            })
        start_values = [_time(row.get("timeStamp")) for row in rows]
        valid_stamps = [v for v in start_values if v]
        duration = (max(valid_stamps)-min(valid_stamps)).total_seconds() if len(valid_stamps)>1 else None
        errors_total = sum(errors.values())
        payload = {
            "total_requests": len(rows), "failed_requests": errors_total,
            "duration_seconds": duration,
            "scenario_name": Path(filename).stem,
            "peak_vus": max((_number(row.get("allThreads")) or 0 for row in rows), default=None),
        }
        points = _timeseries([
            {"timestamp": row.get("timeStamp"), "response_time": row.get("elapsed"),
             "users": row.get("allThreads")}
            for row in rows
        ], filename)
        return _normalize(payload, "JMeter", filename, txns, points)
    # Generic time-series CSV. Accept the first row's labels rather than guessing field meaning.
    txns = []
    if {"transaction", "count"}.issubset({k.lower() for k in first}):
        txns = rows
    return _normalize({}, "CSV", filename, txns, _timeseries(rows, filename))


def parse_excel_report(data: bytes, filename: str) -> PerformanceReport:
    workbook = pd.ExcelFile(io.BytesIO(data))
    payload = {}
    transactions = []
    points = []
    for sheet in workbook.sheet_names:
        frame = workbook.parse(sheet)
        rows = frame.where(pd.notna(frame), None).to_dict(orient="records")
        lower = sheet.lower()
        if "summary" in lower and rows:
            payload.update(rows[0])
        elif "transaction" in lower or "sampler" in lower:
            transactions.extend(rows)
        else:
            points.extend(_timeseries(rows, filename))
    return _normalize(payload, "Excel", filename, transactions, points)


def parse_log_file(data: bytes, filename: str) -> PerformanceReport:
    text = data.decode("utf-8", errors="replace")
    error_lines = [line for line in text.splitlines() if re.search(r"\b(ERROR|FATAL|Exception)\b", line, re.I)]
    points = []
    stamp_pattern = re.compile(r"(\d{4}-\d\d-\d\d[T ][0-9:.+-]+)")
    for line in text.splitlines():
        match = stamp_pattern.search(line)
        if not match:
            continue
        stamp = _time(match.group(1))
        if stamp:
            points.append(TimeSeriesPoint(timestamp=stamp, metric="log_error_event",
                value=1.0 if re.search(r"\b(ERROR|FATAL|Exception)\b", line, re.I) else 0.0,
                unit="events", source=filename, attributes={"message": line[:400]}))
    return _normalize({"failed_requests": len(error_lines)}, "Log", filename, points=points)


def parse_neoload_html_bytes(data: bytes, filename: str) -> PerformanceReport:
    soup = BeautifulSoup(data.decode("utf-8", errors="replace"), "html.parser")
    text = soup.get_text(" ", strip=True)
    payload = {"scenario_name": filename}
    mapping = {
        "total requests": "total_requests",
        "total users launched": "peak_vus",
        "average requests/s": "request_rps",
        "average request response time": "average_response_time_s",
        "total request errors": "failed_requests",
        "error rate": "error_rate_pct",
    }
    for label, key in mapping.items():
        m = re.search(re.escape(label) + r"\s*:?\s*([0-9,.]+)", text, re.I)
        if m:
            payload[key] = _number(m.group(1))
    duration_match = re.search(r"duration\s*:?\s*(\d+):(\d{2})(?::(\d{2}))?", text, re.I)
    if duration_match:
        g = duration_match.groups()
        payload["duration_seconds"] = int(g[0])*60+int(g[1]) if g[2] is None else int(g[0])*3600+int(g[1])*60+int(g[2])
    return _normalize(payload, "NeoLoad HTML", filename)


def ingest_upload(filename: str, data: bytes) -> PerformanceReport:
    suffix = Path(filename).suffix.lower()
    if suffix == ".zip":
        return ingest_neoload_zip(filename, data)
    if suffix in {".html", ".htm"}:
        return parse_neoload_html_bytes(data, filename)
    if suffix in {".csv", ".jtl"}:
        return parse_csv_report(data, filename)
    if suffix in {".json"}:
        return parse_json_report(data, filename)
    if suffix in {".xlsx", ".xls"}:
        return parse_excel_report(data, filename)
    if suffix in {".log", ".txt"}:
        return parse_log_file(data, filename)
    raise ValueError(f"Unsupported file extension: {suffix}")


def ingest_neoload_zip(filename: str, data: bytes) -> PerformanceReport:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        html_names = [name for name in archive.namelist() if name.lower().endswith((".html", ".htm"))]
        if not html_names:
            raise ValueError("ZIP archive contains no HTML report")
        chosen = next((name for name in html_names if name.lower().endswith("summary.html")), None)
        if chosen is None:
            chosen = next((name for name in html_names if name.lower().endswith("index.html")), html_names[0])
        html = archive.read(chosen)
        report = parse_neoload_html_bytes(html, filename)
        # Some NeoLoad report layouts contain a detailed transaction table in another HTML member.
        for name in html_names:
            if name == chosen:
                continue
            detail = BeautifulSoup(archive.read(name).decode("utf-8", errors="replace"), "html.parser")
            for table in detail.find_all("table"):
                headers = [cell.get_text(" ", strip=True).lower() for cell in table.find_all("th")]
                if not headers or not any("avg" in h for h in headers):
                    continue
                frame = pd.read_html(io.StringIO(str(table)))[0]
                rows = frame.where(pd.notna(frame), None).to_dict(orient="records")
                if rows:
                    parsed = _transaction_rows(rows)
                    if parsed:
                        report.transactions = parsed
                        break
            if report.transactions:
                break
        report.source_name = filename
        return report
