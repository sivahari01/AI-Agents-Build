"""Build evidence-grounded prompts and answer report questions."""

from __future__ import annotations

import json

from analyzer.wlm_calculator import (
    calculate_wlm,
    forecast_users_from_prompt,
    format_wlm,
    is_wlm_question,
    calculate_workload_recommendation,
    extract_target_tps,
)

from .ollama_client import OllamaClient
from .prompts import WLM_PROMPT_TEMPLATE


SYSTEM_PROMPT = (
    "You are an experienced performance test engineer. Use only the supplied JSON "
    "as evidence. Never invent metrics or root causes. Clearly label unavailable "
    "data, observations, hypotheses, evidence required, and recommendations. "
    "Keep answers concise, practical, and report-specific."
)


class PerfAIAgent:
    def __init__(self, report: dict, analysis: dict, client: OllamaClient | None = None):
        self.report = report
        self.analysis = analysis
        self.client = client or OllamaClient()

    def context(self) -> str:
        return json.dumps({
            "report": self.report,
            "calculated_analysis": self.analysis,
        }, default=str)

    def analyze(self) -> str:
        prompt = (
            "Analyze this NeoLoad performance report. Identify confirmed observations, "
            "potential bottlenecks, hypotheses, missing evidence, and prioritized actions.\n"
            f"DATA:\n{self.context()}"
        )
        return self.client.generate(prompt, SYSTEM_PROMPT)

    def chat(self, question: str) -> str:
        if is_wlm_question(question):
            forecast_users = forecast_users_from_prompt(question)
            target_tps = extract_target_tps(question)
            if target_tps is not None:
                wlm = calculate_workload_recommendation(
                    self.report,
                    target_tps=target_tps,
                    target_users=forecast_users,
                )
            else:
                wlm = calculate_workload_recommendation(
                    self.report,
                    target_users=forecast_users or self.report.get("max_virtual_users"),
                )
            prompt = WLM_PROMPT_TEMPLATE.format(wlm=json.dumps(wlm, indent=2))
            prompt += (
                f"\nUser request: {question}\n"
                "Do not repeat the JSON. Present a professional workload recommendation with "
                "measured values, Little's Law steps, assumptions, transaction mix, NeoLoad "
                "configuration, and clearly state missing inputs."
            )
            return self.client.generate(prompt, SYSTEM_PROMPT)
        transactions = self.report.get("transactions", [])
        if transactions:
            ranked = sorted(
                transactions,
                key=lambda item: item.get("avg_response_time_s")
                if item.get("avg_response_time_s") is not None else -1,
                reverse=True,
            )
            slowest = ranked[0]
            ranked_summary = {
                "highest_average_transaction": slowest["name"],
                "highest_average_seconds": slowest.get("avg_response_time_s"),
            }
        else:
            ranked_summary = {"highest_average_transaction": None, "highest_average_seconds": None}
        prompt = (
            f"Question: {question}\n"
            "Answer using only the report evidence below. If a metric is unavailable, say so.\n"
            f"PRE-CALCULATED FACT: {json.dumps(ranked_summary)}\n"
            f"DATA:\n{self.context()}"
        )
        return self.client.generate(prompt, SYSTEM_PROMPT)
