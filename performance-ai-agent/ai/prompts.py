WLM_PROMPT_TEMPLATE = """Calculate and explain this workload model.

Python-calculated WLM:
{wlm}

Requirements:
- Explain measured values, assumptions, and recommendations separately.
- Use only the supplied report values and calculations.
- Do not invent missing think time or pacing.
- If target TPS or users were not supplied, ask for that business input before
  recommending a future-test size.
- Explain Little's Law and units.
- Base workload timing on the supplied report duration and observed values.
- State the transaction mix derived from the Python calculation.
- Recommend NeoLoad Population, User Path and Scenario configuration."""
