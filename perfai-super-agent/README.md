# PerfAI — Super Performance Intelligence Agent

PerfAI combines load-test reports, New Relic telemetry, deterministic analysis, and optional local Ollama explanations.

## Features
- NeoLoad ZIP/HTML, JMeter CSV/JTL, JSON, Excel, and text-log ingestion (format-dependent fields remain unavailable when absent).
- Normalized test metrics and transaction summaries.
- Read-only New Relic NerdGraph/NRQL integration with entity discovery.
- Timestamp alignment and Pearson correlation for comparable time series.
- Configurable bottleneck rules and evidence-labelled findings.
- Transaction/iteration Little's Law workload sizing.
- Optional local Ollama chat and HTML/JSON/CSV exports.

## Quick start
```bash
cd perfai-super-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Ollama is optional. Install Ollama separately and pull a small model, e.g. `ollama pull qwen2.5:0.5b`.

## New Relic
Create a New Relic **User API key** with read access. Enter it in the New Relic page or configure `NEW_RELIC_API_KEY` in your environment. Select US or EU region and provide the account ID. The connector uses NerdGraph over HTTPS and executes read-only NRQL queries. Never commit a real key.

Entity discovery and metric availability depend on the account's instrumentation and permissions. PerfAI deliberately does not fabricate missing metrics. NRQL examples are editable; inspect the query and returned attributes before interpreting them.

## Data and limitations
- NeoLoad HTML/ZIP parsing is best-effort across report versions; verify extracted values against the source report.
- JMeter CSV/JTL support recognizes common sample columns. Unsupported formats should be exported to CSV.
- Correlation indicates co-movement, not causation.
- Workload sizing requires a rate and time measurement from the same scope.
- New Relic query schema/attributes vary by instrumentation; use discovered data and adapt NRQL.
- No telemetry is uploaded to an LLM by default. Only the selected report context is sent to a locally configured Ollama endpoint.

## Tests
```bash
pytest -q
```
