from __future__ import annotations
import html, json
from datetime import datetime, timezone

def build_rca_html(report: dict, findings: list[dict], correlation: dict | None=None, ai_summary: str | None=None) -> str:
    esc=html.escape
    rows="".join(f"<tr><td>{esc(str(x.get('title')))}</td><td>{esc(str(x.get('severity')))}</td><td>{esc(str(x.get('evidence')))}</td><td>{esc(str(x.get('next_investigation')))}</td></tr>" for x in findings)
    summary=esc(ai_summary or "AI analysis was not requested.")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>PerfAI RCA</title>
<style>body{{font:15px Arial;margin:36px;color:#172033}}h1,h2{{color:#183153}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #d7dfeb;padding:9px;text-align:left}}th{{background:#edf2f8}}pre{{white-space:pre-wrap}}</style></head><body>
<h1>PerfAI — Performance RCA</h1><p>Generated {datetime.now(timezone.utc).isoformat()}</p>
<h2>Test overview</h2><pre>{esc(json.dumps({k:report.get(k) for k in ['source','scenario_name','duration_seconds','max_virtual_users','total_requests','failed_requests','error_rate_pct','average_response_time_s','p95_response_time_s','p99_response_time_s','average_tps','average_rps']},indent=2))}</pre>
<h2>Potential bottlenecks</h2><table><tr><th>Finding</th><th>Severity</th><th>Evidence</th><th>Next investigation</th></tr>{rows}</table>
<h2>Correlation</h2><pre>{esc(json.dumps((correlation or {}).get('correlations',[]),indent=2))}</pre>
<h2>AI interpretation</h2><pre>{summary}</pre>
<p><b>Interpretation note:</b> Findings are evidence-based indicators. Correlation and threshold breaches do not independently establish causation.</p></body></html>"""
def json_export(report,findings,correlation=None):
    return json.dumps({"report":report,"findings":findings,"correlation":correlation or {}},indent=2,default=str)
