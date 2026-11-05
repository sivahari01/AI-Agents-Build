import pytest
from integrations.newrelic import NewRelicClient,NewRelicError

def test_rejects_missing_key():
    with pytest.raises(NewRelicError): NewRelicClient("","123","US")

def test_rejects_invalid_region():
    with pytest.raises(NewRelicError): NewRelicClient("key","123","APAC")

def test_rejects_non_select_nrql():
    client=NewRelicClient("key","123","US")
    with pytest.raises(NewRelicError): client.run_nrql("DELETE FROM Transaction")
