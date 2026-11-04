import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyzer.bottlenecks import detect_bottlenecks

def test_high_cpu_is_hypothesis_not_confirmed_cause():
    findings=detect_bottlenecks({"average_response_time_s":3.5},[
        {"metric":"cpu_percent","value":95}])
    assert any(x["title"]=="Elevated CPU utilization" for x in findings["findings"])
    assert all(x["classification"]=="hypothesis" for x in findings["findings"])
