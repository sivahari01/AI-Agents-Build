from analyzer.bottlenecks import detect_bottlenecks

def test_cpu_threshold_finding_contains_evidence():
    result=detect_bottlenecks({"cpu_pct":95})
    assert result[0]["metric"]=="cpu_pct"
    assert "crossed configured threshold" in result[0]["evidence"]
