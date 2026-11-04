import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyzer.wlm_calculator import (
    calculate_wlm,
    forecast_users_from_prompt,
    format_wlm,
    is_wlm_question,
    calculate_workload_recommendation,
    extract_target_tps,
)


def test_calculate_hourly_volumes_and_mix():
    report = {
        "scenario_name": "example",
        "duration_seconds": 3600,
        "max_virtual_users": 10,
        "transactions": [
            {"name": "search", "execution_count": 100},
            {"name": "checkout", "execution_count": 50},
        ],
    }

    result = calculate_wlm(report, forecast_users=20)

    assert result["transactions"][0]["observed_per_hour"] == 100
    assert result["transactions"][1]["observed_per_hour"] == 50
    assert result["transactions"][0]["forecast_per_hour"] == 200
    assert result["total_observed_per_hour"] == 150
    assert result["total_forecast_per_hour"] == 300


def test_extract_forecast_users():
    assert forecast_users_from_prompt("Build WLM for 500 users") == 500


def test_wlm_questions_use_fast_local_calculation():
    assert is_wlm_question("Calculate the workload model using past results")
    result = calculate_wlm({
        "duration_seconds": 3600,
        "max_virtual_users": 30,
        "transactions": [{"name": "Launch", "execution_count": 100}],
    }, forecast_users=30)
    output = format_wlm(result)
    assert "| Launch |" in output
    assert "100.0" in output


def test_littles_law_recommendation():
    result = calculate_workload_recommendation(
        {
            "average_tps": 10,
            "max_virtual_users": 20,
            "average_response_time_s": 2,
            "duration_seconds": 300,
            "transactions": [{"name": "search", "execution_count": 80}],
        },
        target_tps=20,
        think_time_s=3,
        pacing_s=1,
    )
    assert result["recommended"]["required_vus"] == 120
    assert result["transactions"][0]["mix_pct"] == 100
    assert result["calculation"]["steps"][0]["substitution"] == "20 x (2 + 3 + 1)"


def test_weighted_mix_tps_and_validation():
    result = calculate_workload_recommendation(
        {
            "duration_seconds": 100,
            "transactions": [
                {"name": "a", "execution_count": 75, "avg_response_time_s": 2},
                {"name": "b", "execution_count": 25, "avg_response_time_s": 4, "error_pct": 6},
            ],
        },
        target_tps=10,
        workload_scope="transaction",
    )
    assert result["transactions"][0]["mix_pct"] == 75
    assert result["transactions"][1]["mix_pct"] == 25
    assert result["measured"]["weighted_average_response_time_s"] == 2.5
    assert result["measured"]["transaction_tps"] == 1
    assert result["validation"]["high_error_transactions"] == ["b"]


def test_extract_target_tps():
    assert extract_target_tps("Calculate workload for 100 TPS") == 100
