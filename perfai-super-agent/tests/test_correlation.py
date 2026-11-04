import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyzer.correlation import correlate_series

def test_correlates_aligned_series():
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    left=[{"timestamp":start+timedelta(minutes=i),"value":i,"metric":"response"} for i in range(8)]
    right=[{"timestamp":start+timedelta(minutes=i),"value":2*i,"metric":"cpu"} for i in range(8)]
    result=correlate_series(left,right,60,min_observations=5)
    assert result["available"]
    assert result["correlation"]>0.99

def test_missing_source_is_reported():
    result=correlate_series([],[],60)
    assert not result["available"]
    assert result["correlation"] is None
