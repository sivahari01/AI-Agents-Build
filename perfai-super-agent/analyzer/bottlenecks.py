"""Configurable, evidence-first bottleneck heuristics."""

from __future__ import annotations


DEFAULT_THRESHOLDS = {
    "cpu_warning_pct": 80.0,
    "cpu_critical_pct": 90.0,
    "memory_warning_pct": 85.0,
    "memory_critical_pct": 95.0,
    "error_warning_pct": 2.0,
    "error_critical_pct": 5.0,
    "response_warning_s": 2.0,
    "response_critical_s": 5.0,
}


def detect_bottlenecks(report: dict, telemetry: list[dict] | None = None,
                       thresholds: dict | None = None) -> dict:
    """Produce potential bottlenecks with explicit evidence and limitations."""
    limits = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    findings = []
    telemetry = telemetry or []

    def emit(category, severity, title, observation, evidence, hypothesis, recommendation, confidence="medium"):
        findings.append({
            "category": category, "severity": severity, "title": title,
            "observation": observation, "evidence": evidence,
            "hypothesis": hypothesis, "recommendation": recommendation,
            "confidence": confidence, "classification": "hypothesis",
        })

    report_error = report.get("error_rate_pct")
    if report_error is not None and report_error >= limits["error_warning_pct"]:
        sev = "critical" if report_error >= limits["error_critical_pct"] else "warning"
        emit("load_test", sev, "Elevated load-test error rate",
             f"Reported error rate is {report_error:.2f}%.",
             [f"Load-test report error_rate_pct={report_error:.3f}"],
             "Application, assertion, test-data, or dependency errors may be contributing.",
             "Inspect failed samples, response codes, assertions, and correlated application logs.")

    avg = report.get("average_response_time_s")
    if avg is not None and avg >= limits["response_warning_s"]:
        sev = "critical" if avg >= limits["response_critical_s"] else "warning"
        emit("load_test", sev, "Elevated average response time",
             f"Average response time is {avg:.3f} seconds.",
             [f"Load-test report average_response_time_s={avg:.3f}"],
             "Application processing, queues, datastore, or downstream latency may be limiting performance.",
             "Compare the slowest transactions with traces and server-side time series.")

    for tx in report.get("transactions", []):
        err = tx.get("error_pct")
        if err is not None and err >= limits["error_warning_pct"]:
            emit("transaction", "critical" if err >= limits["error_critical_pct"] else "warning",
                 f"Errors in {tx.get('name')}",
                 f"{tx.get('name')} reports {err:.2f}% errors.",
                 [f"Transaction={tx.get('name')}", f"Error percentage={err:.3f}",
                  f"Error count={tx.get('error_count')}"],
                 "The transaction may fail due to application behavior or downstream dependency errors.",
                 "Review failed request details and distributed traces for this transaction.")
    grouped = {}
    for point in telemetry:
        metric = str(point.get("metric", "")).lower()
        value = point.get("value")
        if value is None:
            continue
        grouped.setdefault(metric, []).append(float(value))
    for metric, values in grouped.items():
        peak = max(values)
        if "cpu" in metric and peak >= limits["cpu_warning_pct"]:
            emit("infrastructure", "critical" if peak >= limits["cpu_critical_pct"] else "warning",
                 "Elevated CPU utilization", f"Observed CPU peak is {peak:.1f}%.",
                 [f"New Relic metric={metric}", f"Observed peak={peak:.2f}%"],
                 "CPU saturation may be limiting request processing, but correlation with test degradation is required.",
                 "Inspect per-process CPU, thread/worker utilization, and transaction traces.")
        if "memory" in metric and ("percent" in metric or "utilization" in metric or metric.endswith("_pct")) and peak >= limits["memory_warning_pct"]:
            emit("infrastructure", "critical" if peak >= limits["memory_critical_pct"] else "warning",
                 "Elevated memory utilization", f"Observed memory peak is {peak:.1f}%.",
                 [f"New Relic metric={metric}", f"Observed peak={peak:.2f}%"],
                 "Memory pressure may cause GC activity, swapping, or resource contention.",
                 "Inspect heap/working set trends, GC pauses, and host/container memory limits.")
    return {"thresholds": limits, "findings": findings,
            "summary": {"total": len(findings),
                        "critical": sum(x["severity"] == "critical" for x in findings),
                        "warning": sum(x["severity"] == "warning" for x in findings)},
            "limitations": ["Threshold findings are screening signals, not proof of root cause.",
                            "Unavailable or uninstrumented metrics are not assumed to be healthy."]}
