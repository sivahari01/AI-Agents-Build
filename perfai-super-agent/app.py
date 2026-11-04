"""PerfAI — Super Performance Intelligence Agent (Streamlit UI)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from analyzer.bottlenecks import detect_bottlenecks
from analyzer.correlation import correlate_metric_pairs
from analyzer.ingestion import ingest_upload
from analyzer.workload import calculate_workload
from ai.ollama import OllamaClient, OllamaError, SYSTEM_PROMPT, build_analysis_prompt
from config import settings
from integrations.newrelic import NewRelicClient, NewRelicError
from integrations.newrelic_metrics import build_metric_queries, results_to_points
from reports.rca import generate_rca_html

load_dotenv()
st.set_page_config(page_title="PerfAI | Performance Intelligence", page_icon="⚡",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{--navy:#15233b;--blue:#2563eb;--muted:#64748b;--line:#dce4ef}
.stApp{background:#f5f7fb;font-family:Inter,sans-serif;color:#172033}
.block-container{max-width:1500px;padding-top:1.6rem;padding-bottom:3rem}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#15233b,#203657)}
[data-testid="stSidebar"] *{color:#f8fafc}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p{color:#cbd5e1}
[data-testid="stMetric"]{background:white;border:1px solid var(--line);border-radius:12px;padding:14px;box-shadow:0 3px 14px #0f172a0a}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:10px}
.stButton>button,.stDownloadButton>button{border-radius:8px;font-weight:600}
h1,h2,h3{letter-spacing:-.025em}
</style>""", unsafe_allow_html=True)

if "report" not in st.session_state:
    st.session_state.report = None
if "server_points" not in st.session_state:
    st.session_state.server_points = []
if "nr_entities" not in st.session_state:
    st.session_state.nr_entities = []
if "nr_discovered_keys" not in st.session_state:
    st.session_state.nr_discovered_keys = set()
if "chat" not in st.session_state:
    st.session_state.chat = []

PAGES = ["Executive Dashboard", "Report Analyzer", "New Relic", "Server-Side Analysis",
         "Performance Correlation", "Bottleneck Analysis", "Workload Model",
         "AI Performance Assistant", "RCA Report", "Analysis History"]

with st.sidebar:
    st.title("⚡ PerfAI")
    st.caption("Super Performance Intelligence")
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")
    st.divider()
    st.caption("Local AI")
    st.code(settings.ollama_model)
    st.caption("New Relic")
    st.write("Connected" if st.session_state.server_points else "Not connected / no telemetry")

st.title(page)
st.caption("Performance test evidence + APM telemetry + deterministic engineering analysis")

report_model = st.session_state.report
report = report_model.model_dump(mode="json") if report_model else None
analysis = detect_bottlenecks(report, st.session_state.server_points) if report else {"findings": [], "summary": {}}

if page == "Report Analyzer":
    st.subheader("Upload a performance test result")
    uploaded = st.file_uploader("NeoLoad HTML/ZIP · JMeter CSV/JTL · Excel · JSON · Logs",
        type=["html","htm","zip","csv","jtl","xlsx","xls","json","log","txt"])
    if uploaded:
        if uploaded.size > settings.max_upload_mb * 1024 * 1024:
            st.error(f"File exceeds the configured {settings.max_upload_mb} MB upload limit.")
        elif st.button("Parse and analyze report", type="primary"):
            try:
                parsed = ingest_upload(uploaded.name, uploaded.getvalue())
                st.session_state.report = parsed
                st.success(f"Parsed {uploaded.name} ({parsed.source_type})")
                st.rerun()
            except Exception as exc:
                st.error(f"Report parsing failed: {exc}")
    if report:
        st.subheader("Normalized report")
        st.json(report)
        if report.get("warnings"):
            st.warning(" · ".join(report["warnings"]))

elif page == "New Relic":
    st.subheader("Connect to New Relic (read-only)")
    left,right=st.columns([1,1])
    with left:
        region=st.selectbox("Region",["US","EU"],index=0 if settings.new_relic_region=="US" else 1)
        account_default=settings.new_relic_account_id
        account_id=st.text_input("Account ID",value=account_default)
        api_key=st.text_input("User API key",value=settings.new_relic_api_key,type="password",
                              help="Use a New Relic User API key. It is not displayed or logged.")
        search=st.text_input("Search application or entity",placeholder="e.g. checkout-service")
    with right:
        start=st.datetime_input("Start time (UTC)",value=datetime.now()-timedelta(hours=1))
        end=st.datetime_input("End time (UTC)",value=datetime.now())
        st.caption("Choose a window matching the load test. All time-series comparisons are normalized to UTC.")
    client=None
    try:
        if api_key.strip():
            client=NewRelicClient(api_key.strip(),region)
    except ValueError as exc:
        st.error(str(exc))
    c1,c2=st.columns(2)
    with c1:
        if st.button("Test connection",disabled=client is None):
            try:
                result=client.test_connection()
                st.success(f"Connected to New Relic {region}.")
                if result.get("user"): st.caption(f"Authenticated user: {result['user']}")
            except NewRelicError as exc: st.error(str(exc))
    with c2:
        if st.button("Discover entities",disabled=client is None):
            try:
                st.session_state.nr_entities=client.discover_entities(search)
                if st.session_state.nr_entities: st.success(f"Discovered {len(st.session_state.nr_entities)} entities.")
                else: st.warning("No entities matched the search.")
            except NewRelicError as exc: st.error(str(exc))
    entities=st.session_state.nr_entities
    if entities:
        labels={f"{e.get('name')} · {e.get('domain')} · {e.get('guid')}":e for e in entities}
        selected=st.selectbox("Select New Relic entity",list(labels))
        entity=labels[selected]
        st.session_state.nr_entity=entity
        st.json({k:entity.get(k) for k in ("name","guid","type","domain","reporting")})
        if st.button("Discover available metrics"):
            try:
                discovered=client.discover_metric_keys(int(account_id),entity["guid"],"1 hour ago")
                st.session_state.nr_discovered_keys={
                    key for row in discovered for key in row.get("keys",[]) if isinstance(key,str)
                }
                st.info(f"Discovered {len(st.session_state.nr_discovered_keys)} metric keys.")
                st.write(sorted(st.session_state.nr_discovered_keys))
            except (NewRelicError,ValueError,KeyError) as exc: st.error(str(exc))
        if st.button("Fetch discovered server metrics"):
            try:
                start_utc=pd.Timestamp(start).tz_localize("UTC") if pd.Timestamp(start).tzinfo is None else pd.Timestamp(start).tz_convert("UTC")
                end_utc=pd.Timestamp(end).tz_localize("UTC") if pd.Timestamp(end).tzinfo is None else pd.Timestamp(end).tz_convert("UTC")
                since=f"{max(1,int((end_utc-start_utc).total_seconds()/60))} minutes ago"
                query_list=build_metric_queries(entity["guid"],st.session_state.nr_discovered_keys,since)
                points=[]
                for item in query_list:
                    rows=client.run_nrql(int(account_id),item["nrql"])
                    points.extend(results_to_points(rows,item["metric_key"]))
                st.session_state.server_points=points
                st.success(f"Retrieved {len(points)} server-side data points.")
            except (NewRelicError,ValueError,KeyError) as exc: st.error(str(exc))
    st.caption("Metric discovery is account- and instrumentation-dependent. Only exact discovered metric keys are queried.")

elif page == "Executive Dashboard":
    if not report: st.info("Upload a NeoLoad/JMeter report in Report Analyzer to begin.")
    else:
        st.subheader(report.get("scenario_name") or report.get("source_name"))
        cards=[
            ("Peak VUs",report.get("peak_vus"),""),
            ("TPS",report.get("transaction_tps"),""),
            ("RPS",report.get("request_rps"),""),
            ("Avg response",report.get("average_response_time_s")," s"),
            ("P95",report.get("p95_response_time_s")," s"),
            ("Error rate",report.get("error_rate_pct"),"%"),
        ]
        cols=st.columns(3)
        for col,(label,value,unit) in zip(cols,cards):
            col.metric(label,"Unavailable" if value is None else f"{value}{unit}")
        st.subheader("Transaction performance")
        if report.get("transactions"):
            frame=pd.DataFrame([x.model_dump() if hasattr(x,"model_dump") else x for x in report_model.transactions])
            st.dataframe(frame,use_container_width=True,hide_index=True)
            metric="average_response_time_s"
            if metric in frame:
                fig=px.bar(frame,x="name",y=metric,color="error_pct",title="Average transaction response time")
                st.plotly_chart(fig,use_container_width=True)
        else: st.info("Transaction-level metrics were not available in the uploaded report.")
        st.subheader("Intelligence summary")
        st.write(analysis.get("summary",{}))
        if st.session_state.server_points:
            st.success(f"New Relic telemetry points loaded: {len(st.session_state.server_points)}")
        else: st.info("New Relic telemetry is optional. Connect it to enrich the analysis.")

elif page == "Server-Side Analysis":
    if not st.session_state.server_points: st.info("Connect New Relic and fetch metrics to view server-side telemetry.")
    else:
        frame=pd.DataFrame(st.session_state.server_points)
        frame["timestamp"]=pd.to_datetime(frame["timestamp"],utc=True)
        st.metric("Telemetry points",len(frame))
        for metric in sorted(frame["metric"].dropna().unique()):
            subset=frame[frame.metric==metric].sort_values("timestamp")
            st.plotly_chart(px.line(subset,x="timestamp",y="value",title=metric),use_container_width=True)
        st.dataframe(frame,use_container_width=True,hide_index=True)

elif page == "Performance Correlation":
    if not report: st.info("Upload a load-test report first.")
    elif not st.session_state.server_points: st.info("Fetch New Relic metrics to correlate client and server performance.")
    else:
        load_points=[p.model_dump(mode="json") for p in report_model.time_series]
        st.caption("Correlation uses timestamp-aligned values. It does not establish causation.")
        bucket=st.select_slider("Alignment bucket",options=[15,30,60,120,300],value=60,format_func=lambda x:f"{x} seconds")
        results=correlate_metric_pairs(load_points,st.session_state.server_points,bucket)
        useful=[r for r in results if r.get("available")]
        if useful: st.dataframe(pd.DataFrame([{k:v for k,v in r.items() if k!="buckets"} for r in useful]),use_container_width=True)
        else: st.warning("Not enough aligned load-test and server-side time-series observations. Check time window, source timestamps, and sampling frequency.")

elif page == "Bottleneck Analysis":
    if not report: st.info("Upload a performance report first.")
    else:
        with st.expander("Threshold settings"):
            cpu=st.number_input("CPU warning %",0.0,100.0,80.0)
            memory=st.number_input("Memory warning %",0.0,100.0,85.0)
            error=st.number_input("Error warning %",0.0,100.0,2.0)
            response=st.number_input("Average response warning (seconds)",0.0,300.0,2.0)
        analysis=detect_bottlenecks(report,st.session_state.server_points,{
            "cpu_warning_pct":cpu,"memory_warning_pct":memory,
            "error_warning_pct":error,"response_warning_s":response})
        st.metric("Potential findings",analysis["summary"]["total"])
        for item in analysis["findings"]:
            with st.expander(f"{item['severity'].upper()} · {item['title']}"):
                st.write(item["observation"])
                st.write("**Evidence**")
                for evidence in item["evidence"]: st.write(f"- {evidence}")
                st.write("**Hypothesis:**",item.get("hypothesis"))
                st.write("**Recommended investigation:**",item.get("recommendation"))
        st.caption("These are screening findings and hypotheses, not confirmed root causes.")

elif page == "Workload Model":
    st.subheader("Little's Law workload sizing")
    scope=st.radio("Throughput scope",["transaction","iteration"],horizontal=True,
                   help="Transaction uses business transaction TPS. Iteration uses full journey IPS.")
    target=st.number_input("Target transaction TPS / iteration IPS",min_value=0.0,value=100.0,step=1.0)
    response=st.number_input("Average response time (seconds)",min_value=0.0,value=1.0,step=.1)
    think=st.number_input("Total think time per iteration (seconds)",min_value=0.0,value=0.0,step=.5)
    pacing=st.number_input("Pacing per iteration (seconds)",min_value=0.0,value=0.0,step=.5)
    override=st.number_input("Target VU override (0 = calculate)",min_value=0,step=10,value=0)
    sizing=calculate_workload(target,scope,response,
        think_time_s=think if scope=="iteration" else None,
        pacing_s=pacing if scope=="iteration" else None,
        target_users=override or None)
    if sizing["valid"]:
        st.metric("Required virtual users",sizing["required_vus"])
        st.code(f"{sizing['formula']}\nInputs: {json.dumps(sizing['operands'])}\nRaw result: {sizing['required_vus_raw']}")
    else:
        for err in sizing["errors"]+sizing["missing_requirements"]: st.error(err)
    st.caption(sizing["warning"])

elif page == "AI Performance Assistant":
    if not report: st.info("Upload a report to provide evidence context.")
    else:
        client=OllamaClient(settings.ollama_base_url,settings.ollama_model)
        st.caption("AI interpretation is optional. Deterministic calculations and findings remain available without Ollama.")
        for role,message in st.session_state.chat:
            with st.chat_message(role): st.markdown(message)
        question=st.chat_input("Ask about response time, errors, server metrics, or RCA")
        if question:
            st.session_state.chat.append(("user",question))
            with st.chat_message("user"): st.markdown(question)
            try:
                prompt=build_analysis_prompt(report,analysis,[])
                answer=client.explain(SYSTEM_PROMPT,prompt+"\nUser question: "+question)
            except OllamaError as exc: answer=str(exc)
            st.session_state.chat.append(("assistant",answer))
            with st.chat_message("assistant"): st.markdown(answer)

elif page == "RCA Report":
    if not report: st.info("Upload a report first.")
    else:
        st.caption("Generate an evidence-linked report. Add AI interpretation from the assistant when available.")
        corr=[]
        if st.session_state.server_points and report_model.time_series:
            corr=correlate_metric_pairs([p.model_dump(mode="json") for p in report_model.time_series],
                                        st.session_state.server_points)
        try:
            ai_text=st.session_state.get("last_ai_analysis")
        except Exception: ai_text=None
        html=generate_rca_html(report,analysis,corr,ai_text)
        st.components.v1.html(html,height=850,scrolling=True)
        st.download_button("Download RCA HTML",html,file_name="perfai-rca.html",mime="text/html")
        st.download_button("Download normalized data JSON",
            json.dumps({"report":report,"findings":analysis,"correlations":corr},indent=2,default=str),
            file_name="perfai-analysis.json",mime="application/json")

elif page == "Analysis History":
    st.info("History is maintained for the current browser session. Persistent local history can be enabled in a future extension.")
    if report:
        st.write({"source":report.get("source_name"),"scenario":report.get("scenario_name"),
                  "uploaded_report_type":report.get("source_type"),"finding_count":analysis["summary"].get("total",0)})
        st.download_button("Export current analysis",json.dumps({"report":report,"analysis":analysis},indent=2,default=str),
                           file_name="perfai-history-export.json",mime="application/json")
    else: st.caption("No report has been analyzed in this session.")
