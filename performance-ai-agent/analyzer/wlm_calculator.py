"""Calculate a simple workload model from historical performance results."""

from __future__ import annotations

import re
import math
from typing import Iterable


def calculate_wlm(
    report: dict,
    forecast_users: int | None = None,
    measurement_hours: float = 1.0,
) -> dict:
    """Calculate transaction volumes per hour.

    When forecast_users is supplied, volumes are scaled from the recorded peak
    virtual users. Historical results must contain execution duration and user
    counts; unavailable values are returned explicitly as null.
    """
    duration_seconds = report.get("duration_seconds")
    observed_users = report.get("max_virtual_users")
    transactions: Iterable[dict] = report.get("transactions", [])
    rows = []

    for transaction in transactions:
        executions = transaction.get("execution_count")
        hourly = None
        forecast_hourly = None
        if isinstance(executions, (int, float)) and duration_seconds:
            hourly = executions * 3600 / duration_seconds
            if forecast_users and observed_users:
                forecast_hourly = hourly * forecast_users / observed_users

        rows.append({
            "transaction": transaction.get("name"),
            "observed_executions": executions,
            "observed_per_hour": round(hourly, 2) if hourly is not None else None,
            "forecast_users": forecast_users,
            "forecast_per_hour": round(forecast_hourly, 2) if forecast_hourly is not None else None,
        })

    total_observed_hourly = sum(row["observed_per_hour"] or 0 for row in rows)
    total_forecast_hourly = sum(row["forecast_per_hour"] or 0 for row in rows)
    if total_observed_hourly:
        for row in rows:
            row["mix_pct"] = round((row["observed_per_hour"] or 0) / total_observed_hourly * 100, 2)
    else:
        for row in rows:
            row["mix_pct"] = None

    return {
        "basis": "observed executions divided by test duration, then scaled by concurrent users",
        "scenario": report.get("scenario_name"),
        "test_duration_seconds": duration_seconds,
        "observed_peak_users": observed_users,
        "forecast_users": forecast_users,
        "measurement_hours": measurement_hours,
        "transactions": rows,
        "total_observed_per_hour": round(total_observed_hourly * measurement_hours, 2),
        "total_forecast_per_hour": round(total_forecast_hourly * measurement_hours, 2),
    }


def forecast_users_from_prompt(prompt: str) -> int | None:
    match = re.search(r"(?i)(?:users?|vus?)\s*(?:=|:)?\s*(\d[\d,]*)", prompt)
    if not match:
        match = re.search(r"(?i)(\d[\d,]*)\s*(?:users?|vus?)\b", prompt)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def is_wlm_question(prompt: str) -> bool:
    text = prompt.lower()
    return (
        "wlm" in text
        or "workload model" in text
        or ("workload" in text and (
            "model" in text
            or "forecast" in text
            or "calculate" in text
            or "recommend" in text
            or "tps" in text
        ))
    )


def format_wlm(wlm: dict) -> str:
    lines = [
        "## Workload Model",
        "",
        f"- Scenario: **{wlm.get('scenario') or 'Unavailable'}**",
        f"- Test duration: **{wlm.get('test_duration_seconds') or 'Unavailable'} seconds**",
        f"- Observed peak users: **{wlm.get('observed_peak_users') or 'Unavailable'}**",
        f"- Forecast users: **{wlm.get('forecast_users') or wlm.get('observed_peak_users') or 'Unavailable'}**",
        "",
        "| Transaction | Executions | Observed/hour | Mix | Forecast/hour |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in wlm["transactions"]:
        mix = "-" if row["mix_pct"] is None else f"{row['mix_pct']}%"
        observed = row["observed_per_hour"]
        forecast = row["forecast_per_hour"]
        lines.append(
            f"| {row['transaction']} | {row['observed_executions']} | "
            f"{observed if observed is not None else '-'} | {mix} | "
            f"{forecast if forecast is not None else '-'} |"
        )
    lines.append("")
    lines.append(f"**Total observed/hour:** {wlm['total_observed_per_hour']}")
    if wlm["total_forecast_per_hour"]:
        lines.append(f"**Total forecast/hour:** {wlm['total_forecast_per_hour']}")
    lines.append("")
    lines.append("Volumes exclude Init, Actions, and End lifecycle entries.")
    return "\n".join(lines)


def extract_target_tps(prompt: str) -> float | None:
    match = re.search(r"(?i)(?:target\s+)?(?:tps|throughput)\D{0,12}(\d+(?:\.\d+)?)", prompt)
    if match:
        return float(match.group(1))
    match = re.search(r"(?i)(\d+(?:\.\d+)?)\s*(?:tps|transactions?\s*(?:per|/)?\s*sec(?:ond)?s?)", prompt)
    return float(match.group(1)) if match else None


def calculate_workload_recommendation(
    report: dict,
    target_tps: float | None = None,
    target_users: int | None = None,
    think_time_s: float | None = None,
    pacing_s: float | None = None,
    workload_type: str = "constant",
    workload_scope: str = "transaction",
) -> dict:
    """Calculate a validated workload recommendation from measured report values."""
    observed_users = report.get("max_virtual_users")
    duration = report.get("duration_seconds")
    transactions = report.get("transactions", [])
    total_executions = sum(row.get("execution_count") or 0 for row in transactions)

    measured_transaction_tps = (
        total_executions / duration
        if duration and duration > 0 and total_executions
        else None
    )
    measured_rps = (
        report.get("total_requests") / duration
        if report.get("total_requests") is not None and duration and duration > 0
        else report.get("average_requests_per_second")
    )
    iterations = report.get("total_iterations_completed")
    measured_iteration_tps = (
        iterations / duration
        if iterations is not None and duration and duration > 0
        else None
    )

    weighted_numerator = 0
    weighted_count = 0
    transaction_rows = []
    for row in transactions:
        executions = row.get("execution_count") or 0
        mix = executions / total_executions * 100 if total_executions else None
        allocated_tps = target_tps * mix / 100 if target_tps is not None and mix is not None else None
        average_rt = row.get("avg_response_time_s")
        if executions and average_rt is not None:
            weighted_numerator += executions * average_rt
            weighted_count += executions
        transaction_rows.append({
            "transaction": row.get("name"),
            "executions": executions,
            "mix_pct": round(mix, 2) if mix is not None else None,
            "target_tps": round(allocated_tps, 3) if allocated_tps is not None else None,
            "average_response_time_s": average_rt,
            "p95_response_time_s": row.get("p95_response_time_s"),
            "p99_response_time_s": row.get("p99_response_time_s"),
            "error_count": row.get("error_count"),
            "error_pct": row.get("error_pct"),
        })
    weighted_average_rt = (
        weighted_numerator / weighted_count
        if weighted_count
        else report.get("average_response_time_s")
    )

    missing = []
    errors = []
    scope = workload_scope.lower()
    if target_tps is None and target_users is None:
        missing.append("Target TPS or target virtual users")
    if duration is None or duration <= 0:
        errors.append("Test duration is unavailable, so measured TPS cannot be validated.")
    if scope == "iteration":
        response_time_s = report.get("iteration_average_time_s")
        if response_time_s is None:
            missing.append("Iteration average completion time")
        if think_time_s is None:
            missing.append("Complete-journey think time (seconds)")
    else:
        response_time_s = weighted_average_rt
        if response_time_s is None:
            errors.append("Weighted transaction response time is unavailable.")

    required_users = target_users
    steps = []
    if target_users is None and target_tps is not None and response_time_s is not None:
        cycle_time_s = response_time_s + (think_time_s or 0) + (pacing_s or 0)
        required_users = target_tps * cycle_time_s
        steps.append({
            "metric": "Required virtual users",
            "formula": "VUs = throughput x (response time + think time + pacing)",
            "inputs": {
                "throughput": target_tps,
                "response_time_s": response_time_s,
                "think_time_s": think_time_s or 0,
                "pacing_s": pacing_s or 0,
            },
            "substitution": (
                f"{target_tps} x ({response_time_s} + {think_time_s or 0} + {pacing_s or 0})"
            ),
            "result": round(required_users, 3),
            "unit": "virtual users",
        })

    high_error_transactions = [
        row["transaction"] for row in transaction_rows
        if row.get("error_pct") is not None and row["error_pct"] >= 5
    ]
    normalized_type = workload_type.lower()
    peak_users = math.ceil(required_users) if required_users is not None else observed_users
    if normalized_type == "spike" and peak_users is not None:
        peak_users = math.ceil(peak_users * 1.5)
    ramp_up = max(60, round(duration * 0.2)) if duration and normalized_type in {"ramp", "step"} else 60
    sustain = duration if normalized_type != "custom" else None
    ramp_down = 60 if normalized_type in {"ramp", "step", "spike"} else 30

    return {
        "measured": {
            "peak_vus": observed_users,
            "duration_seconds": duration,
            "transaction_tps": round(measured_transaction_tps, 6) if measured_transaction_tps is not None else None,
            "rps": round(measured_rps, 6) if measured_rps is not None else None,
            "iteration_throughput_per_second": round(measured_iteration_tps, 6) if measured_iteration_tps is not None else None,
            "weighted_average_response_time_s": round(weighted_average_rt, 6) if weighted_average_rt is not None else None,
            "report_average_response_time_s": report.get("average_response_time_s"),
        },
        "assumptions": {
            "target_tps": target_tps,
            "think_time_s": think_time_s,
            "pacing_s": pacing_s,
        },
        "recommended": {
            "workload_type": normalized_type,
            "target_tps": target_tps,
            "required_vus": math.ceil(required_users) if required_users is not None else None,
            "baseline_vus": observed_users,
            "peak_vus": peak_users,
            "ramp_up_seconds": ramp_up,
            "sustain_seconds": sustain,
            "ramp_down_seconds": ramp_down,
        },
        "calculation": {
            "method": "Little's Law: VUs = TPS x (response time + think time + pacing)",
            "scope": scope,
            "response_time_s": response_time_s,
            "steps": steps,
        },
        "transactions": transaction_rows,
        "validation": {
            "valid": not errors and required_users is not None,
            "errors": errors,
            "missing_requirements": sorted(set(missing)),
            "high_error_transactions": high_error_transactions,
        },
        "neoload_guidance": {
            "population": f"{report.get('scenario_name') or 'PerfAI'}_WLM",
            "user_path": "Configure measured transaction actions in the reported proportions.",
            "scenario": "Attach the population to a NeoLoad scenario with the recommended load policy.",
            "variation_policy": {
                "constant": "Constant",
                "ramp": "Ramp up",
                "step": "Step",
                "spike": "Custom spike",
            }.get(normalized_type, "Custom"),
        },
    }
