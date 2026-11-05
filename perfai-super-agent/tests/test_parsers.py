import pandas as pd
from analyzer.parsers import parse_jmeter_frame

def test_jmeter_frame():
    df=pd.DataFrame({"elapsed":[100,300],"label":["login","login"],"success":[True,False]})
    result=parse_jmeter_frame(df)
    assert result.total_requests==2 and result.failed_requests==1
