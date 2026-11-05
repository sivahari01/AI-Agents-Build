# PerfAI — Super Performance Intelligence Agent

A modular Streamlit application for performance-test report parsing, read-only New Relic NerdGraph/NRQL access, time-series correlation, rule-based bottleneck indicators, and Little's Law workload sizing.

## Run
```bash
cd perfai-super-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```
New Relic is optional. Configure a New Relic User API key and account ID in the UI or environment. Use only a read-scoped key. Ollama is optional and not yet wired into this first UI milestone. Correlation is not causation. NeoLoad parsing is best-effort; verify extracted values against original report.
## Tests
`pytest -q`
