"""Calculate evidence-based findings from parsed performance data."""

from __future__ import annotations


def analyze_metrics(report: dict, thresholds: dict | None = None) -> dict:
    thresholds = thresholds or {"error_pct": 5.0, "response_time_s": 3.0, "tps_drop_pct": 25.0}
    transactions = report.get("transactions", [])
    findings = []
    bottlenecks = []

    for transaction in transactions:
        name = transaction["name"]
        avg = transaction.get("avg_response_time_s")
        errors = transaction.get("error_count")
        error_pct = transaction.get("error_pct")
        count = transaction.get("execution_count") or 0
        p95 = transaction.get("p95_response_time_s")

        if avg is not None and avg >= thresholds["response_time_s"]:
            findings.append({
                "category": "response_time",
                "severity": "high",
                "transaction": name,
                "evidence": f"Average response time is {avg:g} seconds.",
            })
        if error_pct is not None and error_pct >= thresholds["error_pct"]:
            findings.append({
                "category": "errors",
                "severity": "high" if error_pct >= 10 else "medium",
                "transaction": name,
                "evidence": f"{error_pct:g}% ({errors:g} of {count:g}) executions failed.",
            })
            bottlenecks.append({
                "issue": f"High error rate in {name}",
                "severity": "high" if error_pct >= 10 else "medium",
                "supporting_metrics": f"Error rate {error_pct:g}% ({errors:g} failures)",
                "time_window": "Entire test run",
                "possible_root_cause": "Application, assertion, or dependency failures require transaction-level investigation.",
                "recommendation": "Inspect NeoLoad assertion/error details and application logs for this transaction.",
                "corrective_action": "Fix the failed requests or assertions; retest with the same load profile.",
                "confidence": "potential",
            })

    ordered_slow = sorted(
        [t for t in transactions if t.get("avg_response_time_s") is not None],
        key=lambda t: t["avg_response_time_s"],
        reverse=True,
    )[:5]
    ordered_errors = sorted(
        [t for t in transactions if t.get("error_count") is not None],
        key=lambda t: t["error_count"] or 0,
        reverse=True,
    )[:5]

    return {
        "thresholds": thresholds,
        "findings": findings,
        "bottlenecks": bottlenecks,
        "slowest_transactions": ordered_slow,
        "transactions_with_most_errors": ordered_errors,
    }
