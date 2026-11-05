import math
def size_workload(target_rate,scope,response_time_s,think_time_s=None,pacing_s=None,target_users=None):
    scope=scope.lower().strip(); errors=[]; missing=[]
    if scope not in {"transaction","iteration"}: errors.append("scope must be transaction or iteration")
    if target_rate is not None and target_rate<=0: errors.append("target rate must be greater than zero")
    if target_users is not None and target_users<=0: errors.append("target users must be greater than zero")
    if target_users is None and target_rate is None: missing.append("Target rate or target VUs")
    cycle=None; formula=None; substitution=None
    if target_users is None and response_time_s is None: missing.append("Response time for selected scope")
    if scope=="transaction":
        if target_rate is not None and response_time_s is not None:
            cycle=response_time_s; formula="VUs = transaction TPS x transaction response time"; substitution=f"{target_rate} x {response_time_s}"
    elif scope=="iteration" and target_users is None and target_rate is not None:
        if think_time_s is None: missing.append("Think time per iteration (enter 0 if none)")
        if pacing_s is None: missing.append("Pacing per iteration (enter 0 if none)")
        if response_time_s is not None and think_time_s is not None and pacing_s is not None:
            cycle=response_time_s+think_time_s+pacing_s; formula="VUs = iteration IPS x (iteration response + think time + pacing)"
            substitution=f"{target_rate} x ({response_time_s} + {think_time_s} + {pacing_s})"
    raw=target_users if target_users is not None else (target_rate*cycle if target_rate is not None and cycle is not None else None)
    return {"valid":not errors and not missing and raw is not None,"errors":errors,"missing":missing,"scope":scope,
      "formula":formula or "Little's Law: throughput rate x residence/cycle time","substitution":substitution,
      "cycle_time_s":cycle,"required_vus":math.ceil(raw) if raw is not None else None,"unrounded_vus":raw}
