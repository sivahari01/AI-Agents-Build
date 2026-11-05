from pydantic import BaseModel,Field
class TransactionMetric(BaseModel):
    name:str
    execution_count:int|None=None
    avg_response_time_s:float|None=None
    p90_response_time_s:float|None=None
    p95_response_time_s:float|None=None
    p99_response_time_s:float|None=None
    error_count:int|None=None
    error_pct:float|None=None
class NormalizedReport(BaseModel):
    source:str
    scenario_name:str|None=None
    started_at:str|None=None
    ended_at:str|None=None
    duration_seconds:float|None=None
    max_virtual_users:int|None=None
    total_requests:int|None=None
    failed_requests:int|None=None
    error_rate_pct:float|None=None
    average_response_time_s:float|None=None
    p90_response_time_s:float|None=None
    p95_response_time_s:float|None=None
    p99_response_time_s:float|None=None
    average_tps:float|None=None
    average_rps:float|None=None
    iteration_ips:float|None=None
    iteration_average_time_s:float|None=None
    transactions:list[TransactionMetric]=Field(default_factory=list)
    timeseries:list[dict]=Field(default_factory=list)
    warnings:list[str]=Field(default_factory=list)
    raw_metadata:dict=Field(default_factory=dict)
