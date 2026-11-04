import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyzer.workload import calculate_workload

def test_transaction_scope_excludes_think_and_pacing():
    result=calculate_workload(20,"transaction",2,think_time_s=3,pacing_s=1)
    assert result["required_vus"]==40
    assert result["cycle_time_s"]==2

def test_iteration_scope_includes_delays():
    result=calculate_workload(20,"iteration",2,think_time_s=3,pacing_s=1)
    assert result["required_vus"]==120

def test_iteration_requires_explicit_delays():
    result=calculate_workload(20,"iteration",2)
    assert not result["valid"]
    assert len(result["missing_requirements"])==2

def test_explicit_target_users_override():
    result=calculate_workload(20,"transaction",2,target_users=75)
    assert result["required_vus"]==75
