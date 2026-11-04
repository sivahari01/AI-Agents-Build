"""Evidence-grounded RCA HTML generator."""
from __future__ import annotations
import html
from datetime import datetime,timezone

def generate_rca_html(report:dict,findings:dict,correlations:list[dict],ai_analysis:str|None=None)->str:
 def metric(label,value,unit=""):
  shown="Unavailable" if value is None else f"{value}{unit}"
  return f"<tr><th>{html.escape(label)}</th><td>{html.escape(shown)}</td></tr>"
 rows="".join([metric("Scenario",report.get("scenario_name")),metric("Duration",report.get("duration_seconds")," s"),
  metric("Peak virtual users",report.get("peak_vus")),metric("Total requests",report.get("total_requests")),
  metric("Failed requests",report.get("failed_requests")),metric("Error rate",report.get("error_rate_pct"),"%"),
  metric("Average response time",report.get("average_response_time_s")," s"),
  metric("P95 response time",report.get("p95_response_time_s")," s"),
  metric("P99 response time",report.get("p99_response_time_s")," s"),
  metric("Transaction TPS",report.get("transaction_tps")),metric("Request RPS",report.get("request_rps"))])
 cards=[]
 for item in findings.get("findings",[]):
  evidence="".join(f"<li>{html.escape(str(x))}</li>" for x in item.get("evidence",[]))
  cards.append(f"<article><h3>{html.escape(item.get('title','Finding'))} <small>{html.escape(item.get('severity','unknown'))}</small></h3><p>{html.escape(item.get('observation',''))}</p><ul>{evidence}</ul><p><b>Hypothesis:</b> {html.escape(item.get('hypothesis') or 'Not established')}</p><p><b>Next step:</b> {html.escape(item.get('recommendation') or 'Not specified')}</p></article>")
 corr="".join(f"<tr><td>{html.escape(str(x.get('load_metric')))}</td><td>{html.escape(str(x.get('server_metric')))}</td><td>{html.escape(str(x.get('correlation')))}</td><td>{html.escape(str(x.get('observations')))}</td></tr>" for x in correlations if x.get("available"))
 ai=html.escape(ai_analysis or "AI interpretation was not generated.")
 return f"""<!doctype html><html><head><meta charset="utf-8"><title>PerfAI RCA</title>
<style>body{{font-family:Arial,sans-serif;max-width:1050px;margin:40px auto;padding:0 24px;color:#172033;background:#f7f9fc}}header{{background:#172b4d;color:white;padding:28px;border-radius:14px}}section,article{{background:white;border:1px solid #dce3ee;border-radius:12px;padding:20px;margin:18px 0}}table{{border-collapse:collapse;width:100%}}td,th{{padding:10px;border-bottom:1px solid #e5eaf2;text-align:left}}small{{background:#fff0d9;color:#8a4b00;padding:4px 9px;border-radius:20px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style></head><body>
<header><h1>PerfAI — Performance RCA</h1><p>Generated {datetime.now(timezone.utc).isoformat()}</p><p>Evidence-based analysis. Correlation alone does not establish causation.</p></header>
<section><h2>Performance summary</h2><table>{rows}</table></section>
<section><h2>Bottleneck findings</h2>{''.join(cards) or '<p>No configured threshold findings.</p>'}</section>
<section><h2>Client/server correlation</h2><table><tr><th>Load metric</th><th>Server metric</th><th>Pearson r</th><th>Observations</th></tr>{corr}</table></section>
<section><h2>AI interpretation (draft)</h2><pre>{ai}</pre></section></body></html>"""
