DEFAULT_THRESHOLDS={"cpu_pct":85.0,"memory_pct":90.0,"error_rate_pct":5.0,"response_time_s":2.0,"gc_pause_ms":500.0}
def detect_bottlenecks(metrics,thresholds=None):
    limits={**DEFAULT_THRESHOLDS,**(thresholds or {})}; findings=[]
    descriptions={"cpu_pct":("CPU utilization","Inspect process and thread profiles."),
      "memory_pct":("Memory utilization","Inspect heap, RSS, container limits, and swapping."),
      "error_rate_pct":("Application error rate","Inspect application logs and dependency failures."),
      "response_time_s":("Application response time","Inspect distributed traces and dependency breakdown."),
      "gc_pause_ms":("Garbage-collection pause","Inspect GC frequency and allocation rate.")}
    for key,(title,next_step) in descriptions.items():
        value=metrics.get(key)
        if isinstance(value,(int,float)) and value>=limits[key]:
            findings.append({"title":title,"severity":"high" if value>=limits[key]*1.2 else "medium",
              "metric":key,"observed":value,"threshold":limits[key],
              "evidence":f"{key}={value} crossed configured threshold {limits[key]}.",
              "interpretation":"Potential bottleneck; threshold breach alone does not prove causality.",
              "next_investigation":next_step})
    return findings
