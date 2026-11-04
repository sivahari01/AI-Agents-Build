import json
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.agent import PerfAIAgent
from ai.ollama_client import OllamaClient, OllamaUnavailableError
from analyzer.metrics_analyzer import analyze_metrics
from analyzer.neoload_parser import parse_neoload
from config import OLLAMA_MODEL, OLLAMA_URL
from utils.file_handler import save_upload
from utils.report_generator import generate_transaction_summary
from analyzer.wlm_calculator import calculate_workload_recommendation

UPLOAD_DIR = ROOT / "uploads"
REPORT_DIR = ROOT / "reports"
UPLOAD_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="PerfAI", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {
  --perfai-blue: #2563eb;
  --perfai-navy: #17233c;
  --perfai-text: #172033;
  --perfai-muted: #64748b;
  --perfai-border: #dbe3ef;
}
.stApp { background: #f4f7fb; color: var(--perfai-text); font-family: Inter, sans-serif; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 92rem; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #17233c 0%, #1d2d50 100%); }
[data-testid="stSidebar"] * { color: #f8fafc !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.16); }
[data-testid="stSidebar"] [role="radiogroup"] label { border-radius: 8px; padding: 5px 8px; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(255,255,255,.09); }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #cbd5e1 !important; }
h1, h2, h3 { color: #172033 !important; letter-spacing: -0.025em; }
p, label, span, div { color: inherit; }
.metric-card {
  min-height: 128px; padding: 19px 20px; border: 1px solid var(--perfai-border);
  border-radius: 12px; background: #ffffff; box-shadow: 0 4px 18px rgba(15, 23, 42, .06);
  border-left: 4px solid var(--perfai-blue);
}
.metric-card h4 { color: var(--perfai-muted); margin: 0; font-size: .76rem; text-transform: uppercase; letter-spacing: .08em; }
.metric-card p { color: #172033; margin: 10px 0 0; font-size: 1.9rem; font-weight: 700; }
[data-testid="stDataFrame"], [data-testid="stDataFrameResizable"] {
  border: 1px solid var(--perfai-border); border-radius: 10px; overflow: hidden;
  box-shadow: 0 4px 14px rgba(15,23,42,.04);
}
[data-testid="stFileUploader"] section {
  background: white; border: 1px dashed #94a3b8; border-radius: 12px;
}
[data-testid="stAlert"] { border-radius: 10px; }
.stButton > button, .stDownloadButton > button {
  border-radius: 8px; border: 1px solid var(--perfai-blue); background: var(--perfai-blue); color: white; font-weight: 600;
}
.stButton > button:hover, .stDownloadButton > button:hover { background: #1d4ed8; border-color: #1d4ed8; color: white; }
[data-testid="stChatMessage"] { border: 1px solid var(--perfai-border); border-radius: 12px; background: white; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 12px; background: white; }
</style>
""", unsafe_allow_html=True)


def metric_card(label: str, value: str):
    st.markdown(
        f'<div class="metric-card"><h4>{label}</h4><p>{value}</p></div>',
        unsafe_allow_html=True,
    )


def save_history(report: dict, analysis: dict):
    record = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "scenario": report.get("scenario_name"),
        "report": report,
        "analysis": analysis,
    }
    (REPORT_DIR / f"analysis-{datetime.now():%Y%m%d-%H%M%S}.json").write_text(
        json.dumps(record, indent=2, default=str), encoding="utf-8"
    )


with st.sidebar:
    st.title("⚡ PerfAI")
    st.caption("Local performance analysis agent")
    page = st.radio(
        "Navigation",
        ["Dashboard", "Report Analyzer", "Transaction Analysis", "Performance Metrics",
         "Bottleneck Analysis", "Workload Model", "AI Assistant", "Analysis History"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Ollama model")
    st.code(OLLAMA_MODEL)

st.title(page)
st.caption("Local NeoLoad performance intelligence")

if page == "Report Analyzer" or st.session_state.get("report") is None:
    uploaded = st.file_uploader(
        "Upload NeoLoad HTML or ZIP report",
        type=["html", "htm", "zip"],
        help="The complete NeoLoad report ZIP is recommended.",
    )
    if uploaded:
        try:
            path = save_upload(uploaded, UPLOAD_DIR)
            with st.spinner("Parsing NeoLoad report and calculating metrics..."):
                report = parse_neoload(path)
                analysis = analyze_metrics(report)
            st.session_state.report = report
            st.session_state.analysis = analysis
            save_history(report, analysis)
            st.success(f"Analyzed {uploaded.name}")
        except Exception as exc:
            st.error(f"Unable to analyze this report: {exc}")

report = st.session_state.get("report")
analysis = st.session_state.get("analysis")

if not report and page != "Report Analyzer":
    st.info("Upload a NeoLoad HTML or ZIP report from Report Analyzer to begin.")
    st.stop()

if report:
    transactions = pd.DataFrame(report.get("transactions", []))
    errors = report.get("error_rate_pct")

    if page in {"Dashboard", "Performance Metrics"}:
        cards = [
            ("Virtual users", report.get("max_virtual_users")),
            ("Average TPS", report.get("average_tps")),
            ("Avg response", report.get("average_response_time_s")),
            ("Error rate", errors),
        ]
        cols = st.columns(4)
        for col, (label, value) in zip(cols, cards):
            with col:
                suffix = "%" if label == "Error rate" else ""
                if label == "Avg response" and value is not None:
                    display = f"{value:.3f} s"
                elif value is None:
                    display = "Unavailable"
                else:
                    display = f"{value:g}{suffix}"
                metric_card(label, display)

        if page == "Dashboard":
            st.subheader("Test overview")
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Scenario:** {report.get('scenario_name', 'Unavailable')}")
                st.write(f"**Duration:** {report.get('duration_seconds', 'Unavailable')} seconds")
                st.write(f"**Status:** {report.get('status', 'Unavailable')}")
            with c2:
                st.write(f"**Requests:** {report.get('total_requests', 'Unavailable')}")
                st.write(f"**Failed requests:** {report.get('failed_transactions', 'Unavailable')}")
                st.write(f"**Peak TPS:** {report.get('average_tps', 'Unavailable')} (report average only)")

            if not transactions.empty:
                fig = px.bar(
                    transactions.sort_values("avg_response_time_s", ascending=False),
                    x="name", y="avg_response_time_s", color="error_pct",
                    labels={"avg_response_time_s": "Average response time (s)", "name": "Transaction"},
                    template="plotly_dark",
                )
                fig.update_layout(
                    template="plotly_white",
                    paper_bgcolor="white",
                    plot_bgcolor="white",
                    font={"color": "#172033", "family": "Inter, sans-serif"},
                    title_font={"color": "#172033"},
                    margin={"l": 20, "r": 20, "t": 40, "b": 20},
                )
                st.plotly_chart(fig, use_container_width=True)

    elif page == "Report Analyzer":
        st.subheader("Parsed NeoLoad data")
        st.json(report)

    elif page == "Transaction Analysis":
        st.subheader("Transaction metrics")
        if transactions.empty:
            st.info("No transaction table was found in this report.")
        else:
            show = transactions[
                ["name", "execution_count", "avg_response_time_s", "p95_response_time_s",
                 "p99_response_time_s", "error_count", "error_pct"]
            ].rename(columns={
                "name": "Transaction", "execution_count": "Executions",
                "avg_response_time_s": "Average (s)", "p95_response_time_s": "P95 (s)",
                "p99_response_time_s": "P99 (s)", "error_count": "Errors",
                "error_pct": "Error %",
            })
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.download_button(
                "Download Transaction Summary",
                generate_transaction_summary(report),
                file_name="transaction-summary.html",
                mime="text/html",
            )

    elif page == "Bottleneck Analysis":
        st.subheader("Potential bottlenecks")
        bottlenecks = analysis["bottlenecks"]
        if not bottlenecks:
            st.success("No configured high-error or high-response-time thresholds were exceeded.")
        else:
            st.dataframe(pd.DataFrame(bottlenecks), use_container_width=True, hide_index=True)

    elif page == "Workload Model":
        st.subheader("AI-powered workload model calculator")
        st.caption("Numerical sizing is calculated locally. Missing assumptions remain marked rather than estimated.")

        input_col, assumption_col = st.columns([2, 1])
        with input_col:
            workload_type = st.selectbox(
                "Workload type",
                ["constant", "ramp", "step", "spike", "custom"],
            )
            workload_scope = st.selectbox(
                "Throughput scope",
                ["transaction", "iteration"],
                help="Transaction = business transactions/second. Iteration = complete user journeys/second (IPS).",
            )
            target_label = "Target transaction TPS" if workload_scope == "transaction" else "Target iteration rate (IPS)"
            target_tps = st.number_input(
                target_label,
                min_value=0.0,
                value=None,
                step=1.0,
                placeholder="Enter a business target",
            )
            target_users = st.number_input(
                "Target VUs (optional override)",
                min_value=0,
                value=None,
                step=10,
                placeholder="Optional",
            )
        with assumption_col:
            think_time = st.number_input("Total think time per iteration (seconds)", min_value=0.0, value=None, step=1.0, placeholder="Required for iteration scope")
            pacing = st.number_input("Pacing per iteration (seconds)", min_value=0.0, value=None, step=1.0, placeholder="Enter 0 if no pacing")

        wlm = calculate_workload_recommendation(
            report,
            target_tps=target_tps if target_tps is not None else None,
            target_users=target_users if target_users is not None else None,
            think_time_s=think_time if think_time is not None else None,
            pacing_s=pacing if pacing is not None else None,
            workload_type=workload_type,
            workload_scope=workload_scope,
        )
        recommended = wlm["recommended"]
        validation = wlm.get("validation", {
            "valid": False,
            "errors": ["Calculation did not include validation metadata. Refresh the app and retry."],
            "missing_requirements": [],
            "high_error_transactions": [],
        })
        if validation["missing_requirements"]:
            st.info("Business inputs required: " + "; ".join(validation["missing_requirements"]))
        if validation["high_error_transactions"]:
            st.error(
                "High-error transactions require investigation before scaling: "
                + ", ".join(validation["high_error_transactions"])
            )
        if validation["errors"]:
            st.error(" ".join(validation["errors"]))
        if st.button("Generate AI workload recommendation", type="primary"):
            prompt = (
                f"Create a {workload_scope}-scope workload model for "
                f"{target_tps if target_tps is not None else 'unspecified target rate'} "
                f"using {target_users if target_users is not None else 'unspecified'} target users, "
                f"workload type {workload_type}, think time "
                f"{think_time if think_time is not None else 'not provided'}, and pacing "
                f"{pacing if pacing is not None else 'not provided'}."
            )
            try:
                with st.spinner("Calculating and interpreting workload model..."):
                    recommendation = PerfAIAgent(
                        report, analysis, OllamaClient(OLLAMA_MODEL, OLLAMA_URL)
                    ).chat(prompt)
                st.markdown(recommendation)
            except OllamaUnavailableError as exc:
                st.error(str(exc))
        with st.expander("Technical calculation details"):
            for step in wlm["calculation"]["steps"]:
                st.markdown(f"**{step['metric']}**")
                st.code(
                    f"{step['formula']}\n"
                    f"Substitution: {step['substitution']}\n"
                    f"Result: {step['result']} {step['unit']}"
                )
            st.json({
                "measured": wlm["measured"],
                "transactions": wlm["transactions"],
                "validation": wlm["validation"],
            })

    elif page == "Analysis History":
        files = sorted(REPORT_DIR.glob("analysis-*.json"), reverse=True)
        if not files:
            st.info("No analysis history is available yet.")
        else:
            for file in files[:20]:
                with st.expander(file.stem):
                    st.json(json.loads(file.read_text(encoding="utf-8")))

    elif page == "AI Assistant":
        st.subheader("Ask about the current report")
        if st.button("Calculate WLM from past results"):
            question = "Calculate the workload model using past results and current peak users"
        else:
            question = None
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        for role, content in st.session_state.chat_history:
            with st.chat_message(role):
                st.markdown(content)
        chat_question = st.chat_input("Ask a report-specific question")
        question = chat_question or question
        if question:
            st.session_state.chat_history.append(("user", question))
            with st.chat_message("user"):
                st.markdown(question)
            try:
                client = OllamaClient(OLLAMA_MODEL, OLLAMA_URL)
                reply = PerfAIAgent(report, analysis, client).chat(question)
            except OllamaUnavailableError as exc:
                reply = str(exc)
            st.session_state.chat_history.append(("assistant", reply))
            with st.chat_message("assistant"):
                st.markdown(reply)
