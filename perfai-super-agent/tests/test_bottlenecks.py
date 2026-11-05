from analyzer.bottlenecks import detect_bottlenecks

def test_cpu_threshold_finding():
    result=detect_bottlenecks({"cpu_pct":95})
    assert result and result[0]["metric"]=="cpu_pct"
