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
    """Apply Little's Law only when throughput and time use the same scope.

    Transaction scope: VUs = transaction TPS x weighted transaction response time.
    Iteration scope: VUs = iteration IPS x (iteration response + think time + pacing).
    """
    observed_users = report.get("max_virtual_users")
    duration = report.get("duration_seconds")
    transactions = report.get("transactions", [])
    scope = str(workload_scope).lower().strip()
    errors, missing = [], []

    if scope not in {"transaction", "iteration"}:
        errors.append("Workload scope must be 'transaction' or 'iteration'.")
    if target_tps is not None and target_tps <= 0:
        errors.append("Target throughput must be greater than zero.")
    if target_users is not None and target_users <= 0:
        errors.append("Target virtual users must be greater than zero.")
    if target_tps is None and target_users is None:
        missing.append("Target transaction TPS / iteration IPS or target VU count")

    total_executions = sum(
        row.get("execution_count") or 0 for row in transactions
        if isinstance(row.get("execution_count"), (int, float))
    )
    measured_transaction_tps = (
        total_executions / duration
        if isinstance(duration, (int, float)) and duration > 0 and total_executions > 0
        else None
    )
    measured_rps = (
        report.get("total_requests") / duration
        if report.get("total_requests") is not None
        and isinstance(duration, (int, float)) and duration > 0
        else report.get("average_requests_per_second")
    )
    iterations = report.get("total_iterations_completed")
    measured_iteration_ips = (
        iterations / duration
        if iterations is not None and isinstance(duration, (int, float)) and duration > 0
        else None
    )

    weighted_rt = None
    if transactions and total_executions:
        complete = all(
            not (row.get("execution_count") or 0) or row.get("avg_response_time_s") is not None
            for row in transactions
        )
        if complete:
            weighted_rt = sum(
                (row.get("execution_count") or 0) * row.get("avg_response_time_s", 0)
                for row in transactions
            ) / total_executions
    elif not transactions:
        weighted_rt = report.get("average_response_time_s")

    transaction_rows = []
    for row in transactions:
        count = row.get("execution_count") or 0
        mix = count / total_executions * 100 if total_executions else None
        allocation = target_tps * mix / 100 if target_tps is not None and mix is not None else None
        transaction_rows.append({
            "transaction": row.get("name"), "executions": count,
            "mix_pct": round(mix, 2) if mix is not None else None,
            "target_tps": round(allocation, 3) if allocation is not None else None,
            "average_response_time_s": row.get("avg_response_time_s"),
            "p95_response_time_s": row.get("p95_response_time_s"),
            "p99_response_time_s": row.get("p99_response_time_s"),
            "error_count": row.get("error_count"), "error_pct": row.get("error_pct"),
        })

    response_time_s, cycle_time_s, formula, inputs, substitution = None, None, None, {}, None
    if scope == "transaction":
        response_time_s = weighted_rt
        if target_tps is not None and response_time_s is None:
            missing.append("Complete weighted average transaction response time")
        if target_tps is not None and response_time_s is not None:
            cycle_time_s = response_time_s
            formula = "VUs = target transaction TPS x weighted transaction response time"
            inputs = {"target_transaction_tps": target_tps,
                      "weighted_transaction_response_time_s": response_time_s}
            substitution = f"{target_tps} x {response_time_s}"
    elif scope == "iteration":
        response_time_s = report.get("iteration_average_time_s")
        if target_tps is not None and response_time_s is None:
            missing.append("Average complete-iteration response time (seconds)")
        if target_tps is not None and think_time_s is None:
            missing.append("Total think time per iteration (seconds)")
        if target_tps is not None and pacing_s is None:
            missing.append("Pacing per iteration (seconds; enter 0 if none)")
        if (target_tps is not None and response_time_s is not None
                and think_time_s is not None and pacing_s is not None):
            cycle_time_s = response_time_s + think_time_s + pacing_s
            formula = "VUs = target iteration IPS x (iteration response time + think time + pacing)"
            inputs = {"target_iteration_ips": target_tps, "iteration_response_time_s": response_time_s,
                      "think_time_s": think_time_s, "pacing_s": pacing_s}
            substitution = f"{target_tps} x ({response_time_s} + {think_time_s} + {pacing_s})"

    required_users = float(target_users) if target_users is not None else None
    steps = []
    if target_users is None and target_tps is not None and cycle_time_s is not None and not errors:
        required_users = target_tps * cycle_time_s
        steps.append({"metric": "Required virtual users", "formula": formula, "inputs": inputs,
                      "substitution": substitution, "result": round(required_users, 3),
                      "unit": "virtual users"})
    elif target_users is not None:
        steps.append({"metric": "Target virtual users", "formula": "Use the explicitly supplied target VU count",
                      "inputs": {"target_users": target_users}, "substitution": str(target_users),
                      "result": target_users, "unit": "virtual users"})

    high_error = [row["transaction"] for row in transaction_rows
                  if row.get("error_pct") is not None and row["error_pct"] >= 5]
    normalized_type = str(workload_type).lower()
    required_vus = math.ceil(required_users) if required_users is not None else None
    if normalized_type not in {"constant", "ramp", "step", "spike", "custom"}:
        errors.append("Unsupported workload type.")
    valid = not errors and not missing and required_users is not None
    return {
        "measured": {
            "peak_vus": observed_users, "duration_seconds": duration,
            "transaction_tps": round(measured_transaction_tps, 6) if measured_transaction_tps is not None else None,
            "rps": round(measured_rps, 6) if measured_rps is not None else None,
            "iteration_throughput_per_second": round(measured_iteration_ips, 6) if measured_iteration_ips is not None else None,
            "weighted_average_response_time_s": round(weighted_rt, 6) if weighted_rt is not None else None,
            "report_average_response_time_s": report.get("average_response_time_s"),
        },
        "assumptions": {"target_tps": target_tps,
                        "target_rate_unit": "transaction_tps" if scope == "transaction" else "iteration_ips",
                        "think_time_s": think_time_s, "pacing_s": pacing_s},
        "recommended": {
            "workload_type": normalized_type, "target_tps": target_tps,
            "required_vus": required_vus, "baseline_vus": observed_users, "peak_vus": required_vus,
            "ramp_up_seconds": None, "sustain_seconds": duration if normalized_type != "custom" else None,
            "ramp_down_seconds": None,
        },
        "calculation": {"method": formula or "Little's Law: L = throughput rate x time in the same workload scope",
                        "scope": scope, "response_time_s": response_time_s,
                        "cycle_time_s": cycle_time_s, "steps": steps},
        "transactions": transaction_rows,
        "validation": {
            "valid": valid, "errors": errors, "missing_requirements": sorted(set(missing)),
            "high_error_transactions": high_error,
            "warnings": ["High-error transactions must be investigated before increasing load."] if high_error else [],
        },
        "neoload_guidance": {
            "population": f"{report.get('scenario_name') or 'PerfAI'}_WLM",
            "user_path": "Configure measured transaction actions in the reported proportions.",
            "scenario": "Attach the population to a NeoLoad scenario with the selected load policy.",
            "variation_policy": {"constant": "Constant", "ramp": "Ramp up", "step": "Step",
                                 "spike": "Custom spike"}.get(normalized_type, "Custom"),
        },
    }
