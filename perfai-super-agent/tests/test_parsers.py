import pandas as pd
from analyzer.parsers import parse_jmeter_frame

def test_jmeter_csv_normalization():
    frame=pd.DataFrame({"timeStamp":[1760000000000,1760000010000],"elapsed":[100,300],
                        "label":["login","login"],"success":[True,False],"threadName":["u1","u2"]})
    result=parse_jmeter_frame(frame)
    assert result.total_requests==2
    assert result.failed_requests==1
    assert result.transactions[0].name=="login"
    assert result.transactions[0].avg_response_time_s==0.2

import json
from analyzer.parsers import parse_json_report

def test_prometheus_range_json_becomes_timeseries():
    payload={"status":"success","data":{"resultType":"matrix","result":[
        {"metric":{"__name__":"node_cpu_percent","instance":"host-a"},
         "values":[[1760000000,"70"],[1760000060,"80"]]}
    ]}}
    report=parse_json_report(json.dumps(payload).encode())
    assert report.source=="Prometheus JSON"
    assert report.timeseries[0]["node_cpu_percent"]==70.0
