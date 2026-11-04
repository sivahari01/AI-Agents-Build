from __future__ import annotations

DEFAULT_THRESHOLDS={"cpu_pct":85.0,"memory_pct":90.0,"error_rate_pct":5.0,"response_time_s":2.0,"gc_pause_ms":500.0}

def detect_bottlenecks(metrics: dict, thresholds: dict | None=None) -> list[dict]:
    limits={**DEFAULT_THRESHOLDS,**(thresholds or {})}
    findings=[]
    checks=[
        ("cpu_pct","CPU utilization", "High CPU utilization can indicate compute saturation; inspect process and thread profiles."),
        ("memory_pct","Memory utilization","High memory use may cause pressure or swapping; inspect heap, RSS, and container limits."),
        ("error_rate_pct","Application error rate","Elevated errors may indicate application, dependency, or capacity failures."),
        ("response_time_s","Application response time","Elevated latency warrants trace and dependency breakdown."),
        ("gc_pause_ms","Garbage-collection pause","Long GC pauses can contribute to latency; inspect GC frequency and allocation rate."),
    ]
    for key,title,action in checks:
        value=metrics.get(key)
        if isinstance(value,(int,float)) and value>=limits[key]:
            findings.append({"title":title,"severity":"high" if value>=limits[key]*1.2 else "medium",
                "metric":key,"observed":value,"threshold":limits[key],"evidence":f"{key}={value} crossed configured threshold {limits[key]}.",
                "interpretation":"Potential bottleneck; threshold breach alone does not prove causality.","next_investigation":action})
    return findings
