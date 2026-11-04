import pytest
from integrations.newrelic import NewRelicClient, NewRelicError

def test_nrql_only_accepts_select(monkeypatch):
    client=NewRelicClient("dummy-key","12345")
    monkeypatch.setattr(client,"_graphql",lambda query: {"actor":{"account":{"nrql":{"results":[{"count":3}]}}}})
    assert client.run_nrql("SELECT count(*) FROM Transaction")==[{"count":3}]
    with pytest.raises(NewRelicError):
        client.run_nrql("DELETE FROM Transaction")

def test_timeseries_converts_epoch():
    rows=NewRelicClient.results_to_timeseries([{"beginTimeSeconds":1760000000,"cpuPercent":70}])
    assert rows[0]["timestamp"].endswith("+00:00")
    assert rows[0]["cpuPercent"]==70
