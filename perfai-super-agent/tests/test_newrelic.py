import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from integrations.newrelic import NewRelicClient
from integrations.newrelic_metrics import build_metric_queries

def test_region_validation():
    with pytest.raises(ValueError):
        NewRelicClient("test-key","AP")

def test_read_only_nrql_validation():
    client=NewRelicClient("test-key","US")
    with pytest.raises(ValueError):
        client.run_nrql(123,"DELETE FROM Metric")

def test_metric_queries_use_only_discovered_keys():
    queries=build_metric_queries("guid-123",{"cpuPercent"})
    assert len(queries)==1
    assert queries[0]["metric_key"]=="cpuPercent"
