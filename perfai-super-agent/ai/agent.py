from __future__ import annotations
import json
from ai.ollama import generate

SYSTEM="""You are PerfAI, a senior performance engineering analyst.
Use only supplied evidence. Never invent measurements, New Relic attributes, or root causes.
Separate observations, hypotheses, confidence, evidence gaps, and recommended next checks.
Correlation is not causation. Mention units and time windows. Be concise and technically precise."""

def analyze_evidence(report: dict, findings: list[dict], correlations: dict | None=None) -> str:
    context={"performance_report":report,"rule_based_findings":findings,"correlation":correlations or {}}
    prompt=("Analyze the performance evidence. Provide an executive summary, key observations, "
            "ranked bottleneck hypotheses, evidence supporting each, evidence gaps, and prioritized next actions. "
            "Do not restate raw JSON.\nEVIDENCE:\n"+json.dumps(context,default=str)[:30000])
    return generate(prompt,SYSTEM)

def answer_question(question: str, report: dict, newrelic: list[dict] | None=None) -> str:
    context={"report":report,"new_relic_samples":newrelic or []}
    return generate("Answer the engineer's question using only this evidence. If unavailable, say so. "
                    f"Question: {question}\nEvidence: {json.dumps(context,default=str)[:25000]}",SYSTEM)
