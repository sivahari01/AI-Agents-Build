"""Scope-correct Little's Law workload sizing."""

from __future__ import annotations

import math


def calculate_workload(target_rate: float, scope: str,
                       response_time_s: float | None,
                       think_time_s: float | None = None,
                       pacing_s: float | None = None,
                       target_users: int | None = None) -> dict:
    scope = scope.lower().strip()
    errors, missing = [], []
    if target_rate <= 0:
        errors.append("Target rate must be greater than zero.")
    if scope not in {"transaction", "iteration"}:
        errors.append("Scope must be transaction or iteration.")
    if target_users is not None and target_users <= 0:
        errors.append("Target users must be greater than zero.")
    cycle = response_time_s
    formula = None
    operands = {}
    if scope == "transaction":
        formula = "VUs = transaction TPS x average transaction response time"
        if response_time_s is None:
            missing.append("Average transaction response time")
        else:
            operands = {"transaction_tps": target_rate, "transaction_response_time_s": response_time_s}
    elif scope == "iteration":
        formula = "VUs = iteration IPS x (iteration response time + think time + pacing)"
        if response_time_s is None:
            missing.append("Complete iteration response time")
        if think_time_s is None:
            missing.append("Total think time per iteration (enter 0 if none)")
        if pacing_s is None:
            missing.append("Pacing per iteration (enter 0 if none)")
        if response_time_s is not None and think_time_s is not None and pacing_s is not None:
            cycle = response_time_s + think_time_s + pacing_s
            operands = {"iteration_ips": target_rate, "iteration_response_time_s": response_time_s,
                        "think_time_s": think_time_s, "pacing_s": pacing_s}
    raw_vus = target_users if target_users is not None else (
        target_rate * cycle if cycle is not None and not errors else None)
    if raw_vus is None and not missing and target_users is None:
        missing.append("Sizing inputs")
    return {"valid": not errors and not missing and raw_vus is not None,
            "errors": errors, "missing_requirements": missing, "scope": scope,
            "formula": formula, "operands": operands, "cycle_time_s": cycle,
            "required_vus_raw": raw_vus,
            "required_vus": math.ceil(raw_vus) if raw_vus is not None else None,
            "target_users_override": target_users,
            "warning": "Little's Law requires throughput and residence time from the same workload scope."}
