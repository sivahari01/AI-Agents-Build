# PerfAI

PerfAI is a local Streamlit application for analyzing NeoLoad HTML and ZIP reports with Ollama.

## Requirements

- Ubuntu Linux with Python 3.10 or newer
- Ollama
- At least 8 GB RAM (16 GB is sufficient for the default CPU model)

## Setup

```bash
cd /workspaces/AI-Agents-Build/performance-ai-agent
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

In another terminal:

```bash
cd /workspaces/AI-Agents-Build/performance-ai-agent
ollama pull qwen2.5:0.5b
source .venv/bin/activate
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Open port 8501 in the Codespace Ports panel.

## Test the parser

```bash
python3 -m pytest -q
```

The parser test uses `../Neoload-AI -Agent/summary.zip`.

## Verify Ollama

```bash
ollama list
curl http://127.0.0.1:11434/api/generate \
  -d '{"model":"qwen2.5:0.5b","prompt":"Reply with PerfAI OK","stream":false}'
```

## Using the dashboard

1. Open **Report Analyzer**.
2. Upload a NeoLoad `.html`, `.htm`, or `.zip` report.
3. Review Dashboard, Transaction Analysis, and Bottleneck Analysis.
4. Ask report-specific questions in AI Assistant.

All AI inference runs locally through Ollama. Ollama and the model are never sent report data outside the workspace.
