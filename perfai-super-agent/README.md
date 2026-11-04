# PerfAI — Super Performance Intelligence Agent

A local-first performance engineering application. PerfAI parses load-test reports, discovers New Relic telemetry, aligns client/server time series, detects evidence-backed bottlenecks, and prepares RCA drafts. Python owns the calculations; the local Ollama model explains the evidence.

## Features

- NeoLoad HTML/ZIP, JMeter CSV/JTL, Excel, JSON, and application log ingestion
- Normalized performance report model with explicit missing values
- New Relic NerdGraph entity discovery and NRQL metric retrieval (read-only)
- Time-bucketed correlation between load-test and APM metrics
- Configurable heuristic bottleneck analysis; correlation is not presented as causation
- Transaction TPS and iteration IPS workload sizing using scope-correct Little's Law
- Local Ollama/Qwen report assistant
- HTML RCA export and analysis data download
- Offline/sample-data mode when New Relic or Ollama is not configured

## Requirements

- Python 3.10+
- 8 GB RAM minimum; 16 GB recommended for local CPU inference
- Ollama is optional; New Relic is optional

## Run locally

```bash
cd perfai-super-agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

For local AI, install Ollama, then run:

```bash
ollama pull qwen2.5:0.5b
ollama serve
```

Set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` in `.env` when needed.

## New Relic setup

1. Create a New Relic **User API key** with permissions appropriate to read account data.
2. Set `NEW_RELIC_ACCOUNT_ID`, `NEW_RELIC_API_KEY`, and `NEW_RELIC_REGION=US|EU` in `.env`.
3. Restart PerfAI, open **New Relic**, and run **Test connection**.
4. Discover entities. Select an entity GUID or use the entity search.
5. Select a time window and retrieve telemetry.

The connector uses NerdGraph at the region-specific New Relic endpoint. Metric attributes are discovered from the selected entity before queries are composed. NRQL metric names are configurable because available event types and attributes depend on installed agents and integrations. PerfAI does not enable instrumentation or mutate New Relic resources.

Never commit `.env` or paste API keys into issues or chat. The UI accepts a key for the current session, but persistent deployment should use Streamlit secrets or environment variables.

## Test

```bash
python -m pytest -q
```

All New Relic tests use mocked HTTP responses. The application can be explored without New Relic credentials.

## RCA interpretation policy

PerfAI labels:
- **Observation**: directly measured in a source report or telemetry response.
- **Correlation**: two time series move together during an aligned time window.
- **Hypothesis**: plausible explanation that needs corroboration.
- **Confirmed root cause**: only when direct evidence supports the causal claim.

Missing telemetry stays missing. Correlation alone is not proof of causation. CPU/memory/latency thresholds are configurable and are not treated as universal capacity limits.
