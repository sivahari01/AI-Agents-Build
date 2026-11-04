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
