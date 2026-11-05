from analyzer.correlation import correlate_timeseries

def test_correlation_aligns_series():
    load=[{"timestamp":f"2026-01-01T00:00:0{i}Z","response_time_s":i} for i in range(1,6)]
    apm=[{"timestamp":f"2026-01-01T00:00:0{i}Z","cpu_pct":i*10} for i in range(1,6)]
    result=correlate_timeseries(load,apm,bucket="1s")
    assert result["aligned"]
    assert result["correlations"][0]["pearson_r"]==1.0
