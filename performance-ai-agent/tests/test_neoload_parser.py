import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyzer.neoload_parser import parse_neoload

SAMPLE = Path(__file__).resolve().parents[2] / "Neoload-AI -Agent" / "summary.zip"


def test_sample_report_values():
    report = parse_neoload(SAMPLE)
    assert report["scenario_name"] == "ConCurrent_Fetch"
    assert report["duration_seconds"] == 29
    assert report["max_virtual_users"] == 30
    assert report["total_requests"] == 95
    assert report["error_rate_pct"] == 15.8
    assert report["failed_transactions"] == 15
    assert {t["name"] for t in report["transactions"]} >= {"Launch", "login"}
    assert "Init" not in {t["name"] for t in report["transactions"]}
    assert "Actions" not in {t["name"] for t in report["transactions"]}
    assert "End" not in {t["name"] for t in report["transactions"]}
