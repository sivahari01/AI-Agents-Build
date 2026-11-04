"""Generate the aggregate transaction summary as HTML."""

from __future__ import annotations

import html


def generate_transaction_summary(report: dict) -> str:
    duration = report.get("duration_seconds") or 0
    transactions = []

    for transaction in report.get("transactions", []):
        count = transaction.get("execution_count") or 0
        errors = transaction.get("error_count") or 0
        passed = max(count - errors, 0)
        tps = passed / duration if duration else 0
        transactions.append({
            **transaction,
            "pass_count": passed,
            "tps": tps,
            "tpm": tps * 60,
        })

    total_count = sum(row["execution_count"] or 0 for row in transactions)
    total_errors = sum(row["error_count"] or 0 for row in transactions)
    total_passed = sum(row["pass_count"] for row in transactions)
    total_tps = sum(row["tps"] for row in transactions)
    total_error_rate = total_errors / total_count * 100 if total_count else 0

    rows = []
    for row in transactions:
        avg = row.get("avg_response_time_s")
        avg_class = " class=\"highlight\"" if avg is not None and avg > 3 else ""
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['name']))}</td>"
            f"<td>{row['tps']:.2f}</td>"
            f"<td>{round(row['tpm'])}</td>"
            f"<td>{row.get('min_response_time_s', '-') or '-'}</td>"
            f"<td{avg_class}>{avg if avg is not None else '-'}</td>"
            f"<td>{row.get('max_response_time_s', '-') or '-'}</td>"
            f"<td>{row.get('p95_response_time_s', '-') or '-'}</td>"
            f"<td>{row['execution_count'] or 0}</td>"
            f"<td>{row['pass_count']}</td>"
            f"<td>{row['error_count'] or 0}</td>"
            f"<td>{row.get('error_pct', total_error_rate) if total_count else 0}</td>"
            "</tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>PerfAI Transaction Summary</title>
<style>
body{{font-family:Arial,sans-serif;background:#f4f7fb;color:#172033;margin:24px}}
.container{{max-width:1400px;margin:auto;background:white;padding:24px;border-radius:10px}}
table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #dbe3ef;padding:9px;text-align:right}}
th:first-child,td:first-child{{text-align:left}}thead th{{background:#344956;color:white}}
tfoot td{{background:#eaf0f7;font-weight:bold}}.highlight{{color:#c62828;font-weight:bold}}
</style></head><body><div class="container">
<h1>Transaction Summary</h1>
<table><thead><tr>
<th>Transaction Action Name</th><th>TPS</th><th>TPM</th><th>Min (s)</th><th>Avg (s)</th>
<th>Max (s)</th><th>P95 (s)</th><th>Count</th><th>Pass Count</th><th>Errors</th><th>Error Rate (%)</th>
</tr></thead><tbody>{''.join(rows)}</tbody><tfoot><tr>
<td>Summary</td><td>{total_tps:.2f}</td><td>{round(total_tps * 60)}</td><td>-</td><td>-</td><td>-</td>
<td>-</td><td>{total_count}</td><td>{total_passed}</td><td>{total_errors}</td>
<td>{total_error_rate:.2f}</td></tr></tfoot></table></div></body></html>"""
