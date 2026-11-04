from analyzer.workload import size_workload

def test_transaction_scope_excludes_think_and_pacing():
    result=size_workload(20,"transaction",2,think_time_s=3,pacing_s=1)
    assert result["required_vus"]==40
    assert result["cycle_time_s"]==2

def test_iteration_scope_includes_explicit_delays():
    result=size_workload(20,"iteration",2,think_time_s=3,pacing_s=1)
    assert result["required_vus"]==120

def test_iteration_requires_delay_assumptions():
    result=size_workload(20,"iteration",2)
    assert not result["valid"]
    assert result["required_vus"] is None

def test_target_users_are_explicit_override():
    result=size_workload(None,"transaction",None,target_users=35)
    assert result["required_vus"]==35
