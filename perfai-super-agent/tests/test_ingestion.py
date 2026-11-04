import io, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyzer.ingestion import ingest_upload

def test_parse_json_preserves_missing_values():
    report=ingest_upload("sample.json",json.dumps({"scenario_name":"load","total_requests":25,
        "transactions":[{"name":"checkout","execution_count":4,"avg_response_time_s":1.25}]}).encode())
    assert report.scenario_name=="load"
    assert report.total_requests==25
    assert report.transactions[0].average_response_time_s==1.25
    assert report.p95_response_time_s is None

def test_parse_jmeter_csv():
    csv=b"timeStamp,elapsed,label,responseCode,success,allThreads\n1700000000000,250,search,200,true,10\n1700000001000,500,search,500,false,10\n"
    report=ingest_upload("jmeter.csv",csv)
    assert report.source_type=="JMeter"
    assert report.total_requests==2
    assert report.failed_requests==1
    assert report.transactions[0].execution_count==2
    assert report.transactions[0].error_pct==50
