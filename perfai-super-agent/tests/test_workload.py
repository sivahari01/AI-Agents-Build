from analyzer.workload import size_workload

def test_transaction_scope():
    assert size_workload(20,"transaction",2,3,1)["required_vus"]==40

def test_iteration_scope():
    assert size_workload(20,"iteration",2,3,1)["required_vus"]==120

def test_missing_iteration_delays():
    result=size_workload(20,"iteration",2)
    assert not result["valid"] and result["required_vus"] is None
