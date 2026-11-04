from __future__ import annotations
import json
import pandas as pd
import plotly.express as px
import streamlit as st

from config import NEW_RELIC_API_KEY, NEW_RELIC_ACCOUNT_ID, NEW_RELIC_REGION, OLLAMA_MODEL
from analyzer.parsers import parse_upload
from analyzer.bottlenecks import detect_bottlenecks
from analyzer.correlation import correlate_timeseries
from analyzer.workload import size_workload
from analyzer.comparison import compare_reports
from integrations.newrelic import NewRelicClient, NewRelicError
from ai.agent import analyze_evidence, answer_question
from ai.ollama import OllamaError
from reports.generator import build_rca_html, json_export
from reports.exporters import build_excel, build_pdf

st.set_page_config(page_title="PerfAI | Super Performance Intelligence",page_icon="⚡",layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
.stApp{background:#f4f7fb;font-family:Inter,sans-serif;color:#172033}
.block-container{max-width:1500px;padding-top:1.5rem}
[data-testid="stSidebar"]{background:#14243d}
[data-testid="stSidebar"] *{color:#f8fafc}
[data-testid="stMetric"]{background:white;border:1px solid #dce4ef;padding:15px;border-radius:12px}
div[data-testid="stVerticalBlockBorderWrapper"]{background:white;border:1px solid #dce4ef;border-radius:12px}
h1,h2,h3{letter-spacing:-.03em}
</style>
""",unsafe_allow_html=True)

def as_dict(report):
    return report.model_dump() if hasattr(report,"model_dump") else report

def current_report():
    return st.session_state.get("perfai_report")

with st.sidebar:
    st.title("⚡ PerfAI")
    st.caption("Super Performance Intelligence Agent")
    page=st.radio("Workspace",["Overview","Report Analyzer","New Relic","Server-side Analysis",
        "Correlation","Bottleneck Analysis","Workload Model","Compare Runs","AI Assistant","RCA Report"])
    st.divider()
    st.caption("Local AI")
    st.code(OLLAMA_MODEL)
    if st.button("Clear session data"):
        for key in ["perfai_report","newrelic_results","newrelic_entities","correlations","findings","ai_summary"]:
            st.session_state.pop(key,None)
        st.rerun()

st.title(page)
st.caption("Load-test evidence + APM telemetry + deterministic engineering analysis")
report=current_report()
report_data=as_dict(report) if report else None

if page=="Overview":
    if not report_data:
        st.info("Start in Report Analyzer and upload a NeoLoad, JMeter, JSON, Excel, or log file.")
    else:
        st.subheader(report_data.get("scenario_name") or "Performance test")
        metrics=[("Virtual users",report_data.get("max_virtual_users")),
                 ("Requests",report_data.get("total_requests")),
                 ("Avg response (s)",report_data.get("average_response_time_s")),
                 ("P95 (s)",report_data.get("p95_response_time_s")),
                 ("Error rate (%)",report_data.get("error_rate_pct")),
                 ("TPS",report_data.get("average_tps"))]
        cols=st.columns(3)
        for col,(label,value) in zip(cols,metrics):
            col.metric(label,"Unavailable" if value is None else f"{value:,.3f}" if isinstance(value,(int,float)) else str(value))
        st.write("**Source:**",report_data.get("source")," | **Duration:**",report_data.get("duration_seconds") or "Unavailable","seconds")
        if report_data.get("transactions"):
            df=pd.DataFrame(report_data["transactions"])
            st.subheader("Transaction performance")
            st.dataframe(df,use_container_width=True,hide_index=True)
            if "avg_response_time_s" in df:
                st.plotly_chart(px.bar(df,x="name",y="avg_response_time_s",color="error_pct",
                    title="Average transaction response time (seconds)"),use_container_width=True)
        if report_data.get("warnings"):
            for warning in report_data["warnings"]: st.warning(warning)
        if st.session_state.get("newrelic_results"):
            st.success(f"New Relic telemetry loaded: {len(st.session_state.newrelic_results)} records")

elif page=="Report Analyzer":
    st.subheader("Upload performance test evidence")
    upload=st.file_uploader("NeoLoad ZIP/HTML · JMeter CSV/JTL · Excel · JSON · application LOG/TXT",
        type=["zip","html","htm","csv","jtl","xlsx","xls","json","log","txt"])
    if upload and st.button("Parse report",type="primary"):
        try:
            parsed=parse_upload(upload.name,upload.getvalue())
            st.session_state.perfai_report=parsed.model_dump()
            st.session_state.pop("correlations",None); st.session_state.pop("findings",None)
            st.success(f"Parsed {upload.name}")
            st.rerun()
        except Exception as exc: st.error(f"Unable to parse report: {exc}")
    if report_data:
        st.subheader("Normalized report")
        st.json(report_data)
        st.download_button("Download normalized JSON",json.dumps(report_data,indent=2,default=str),
            file_name="perfai-normalized-report.json",mime="application/json")

elif page=="New Relic":
    st.subheader("New Relic read-only connection")
    st.caption("Use a New Relic User API key. Credentials are used only for this session and are never added to reports.")
    c1,c2=st.columns(2)
    with c1:
        account=st.text_input("Account ID",value=str(NEW_RELIC_ACCOUNT_ID))
        region=st.selectbox("Region",["US","EU"],index=0 if NEW_RELIC_REGION!="EU" else 1)
    with c2:
        api_key=st.text_input("User API key",value=NEW_RELIC_API_KEY,type="password")
        entity_guid=st.text_input("Entity GUID (optional)")
    test_connection=st.button("Test connection")
    if test_connection:
        if api_key and account:
            try:
                client=NewRelicClient(api_key,account,region)
                result=client.test_connection()
                st.session_state.nr_client=client
                st.success(f"Connected to New Relic account {result['account_id']} ({region}).")
            except NewRelicError as exc: st.error(str(exc))
        else: st.warning("Enter account ID and User API key.")
    client=st.session_state.get("nr_client")
    if client:
        st.markdown("#### Entity discovery")
        search=st.text_input("Search application / service name")
        if st.button("Discover entities"):
            try:
                entities=client.discover_entities(search or "")
                st.session_state.newrelic_entities=entities
                st.dataframe(pd.DataFrame(entities),use_container_width=True,hide_index=True)
            except NewRelicError as exc: st.error(str(exc))
        if st.session_state.get("newrelic_entities"):
            st.dataframe(pd.DataFrame(st.session_state.newrelic_entities),use_container_width=True,hide_index=True)
        st.markdown("#### NRQL query")
        default_query=f"SELECT average(duration) AS avg_duration, rate(count(*), 1 minute) AS rpm FROM Transaction WHERE entity.guid = '{entity_guid}' TIMESERIES 1 minute SINCE 60 minutes ago" if entity_guid else "SELECT count(*) FROM Transaction SINCE 60 minutes ago"
        nrql=st.text_area("Read-only NRQL",value=default_query,height=110)
        if st.button("Fetch New Relic metrics",type="primary"):
            try:
                results=client.run_nrql(nrql)
                st.session_state.newrelic_results=results
                st.session_state.newrelic_timeseries=client.results_to_timeseries(results)
                st.success(f"Retrieved {len(results)} result rows.")
            except NewRelicError as exc: st.error(str(exc))
        if st.session_state.get("newrelic_results"):
            st.dataframe(pd.json_normalize(st.session_state.newrelic_results),use_container_width=True,hide_index=True)
            st.download_button("Download New Relic JSON",json.dumps(st.session_state.newrelic_results,indent=2,default=str),
                file_name="newrelic-metrics.json",mime="application/json")
    else:
        st.info("Test the connection to enable entity discovery and NRQL queries.")

elif page=="Server-side Analysis":
    st.subheader("Server-side telemetry")
    results=st.session_state.get("newrelic_results",[])
    if not results:
        st.info("Connect to New Relic and fetch metrics first.")
    else:
        frame=pd.json_normalize(results)
        st.dataframe(frame,use_container_width=True,hide_index=True)
        st.caption("New Relic attributes depend on installed agents and instrumentation. Only returned attributes are displayed.")
        st.download_button("Export server-side metrics",frame.to_csv(index=False),file_name="server-metrics.csv")

elif page=="Correlation":
    st.subheader("Client-side / server-side time correlation")
    load_ts=(report_data or {}).get("timeseries",[]) if report_data else []
    apm_ts=st.session_state.get("newrelic_timeseries",[])
    st.write(f"Load-test time-series points: **{len(load_ts)}** · New Relic time-series points: **{len(apm_ts)}**")
    bucket=st.selectbox("Alignment bucket",["10s","30s","1min","5min"],index=2)
    if st.button("Align and correlate",type="primary"):
        result=correlate_timeseries(load_ts,apm_ts,bucket=bucket)
        st.session_state.correlations=result
    result=st.session_state.get("correlations")
    if result:
        if result["correlations"]: st.dataframe(pd.DataFrame(result["correlations"]),use_container_width=True,hide_index=True)
        else: st.warning("No statistically comparable numeric series with sufficient overlapping samples were found.")
        if result["aligned"]:
            df=pd.DataFrame(result["aligned"])
            st.dataframe(df,use_container_width=True,hide_index=True)
            numeric=[c for c in df.columns if c!="timestamp" and pd.api.types.is_numeric_dtype(df[c])]
            if numeric: st.plotly_chart(px.line(df,x="timestamp",y=numeric,title="Aligned telemetry"),use_container_width=True)
        for warning in result.get("warnings",[]): st.warning(warning)

elif page=="Bottleneck Analysis":
    st.subheader("Rule-based bottleneck indicators")
    st.caption("Enter actual New Relic values or paste metrics retrieved from your monitoring system.")
    c1,c2,c3=st.columns(3)
    with c1: cpu=st.number_input("CPU utilization (%)",0.0,100.0,value=0.0)
    with c2: memory=st.number_input("Memory utilization (%)",0.0,100.0,value=0.0)
    with c3: error=st.number_input("Application error rate (%)",0.0,100.0,value=0.0)
    c4,c5=st.columns(2)
    with c4: rt=st.number_input("Application response time (seconds)",0.0,value=0.0)
    with c5: gc=st.number_input("GC pause (ms)",0.0,value=0.0)
    if st.button("Analyze server metrics",type="primary"):
        values={k:v for k,v in {"cpu_pct":cpu,"memory_pct":memory,"error_rate_pct":error,
                                "response_time_s":rt,"gc_pause_ms":gc}.items() if v>0}
        st.session_state.findings=detect_bottlenecks(values)
    findings=st.session_state.get("findings",[])
    if findings: st.dataframe(pd.DataFrame(findings),use_container_width=True,hide_index=True)
    elif "findings" in st.session_state: st.success("No configured thresholds were exceeded by the supplied values.")
    with st.expander("Configure thresholds"):
        st.write("Default thresholds: CPU 85%, memory 90%, errors 5%, response time 2 seconds, GC pause 500 ms. Edit analyzer/bottlenecks.py to tune these for your service.")

elif page=="Workload Model":
    st.subheader("Little's Law workload sizing")
    scope=st.selectbox("Scope",["transaction","iteration"])
    c1,c2=st.columns(2)
    with c1:
        rate=st.number_input("Target transaction TPS / iteration IPS",min_value=0.0,value=0.0)
        response=st.number_input("Response time for selected scope (seconds)",min_value=0.0,value=0.0)
    with c2:
        think=st.number_input("Total think time per iteration (seconds)",min_value=0.0,value=0.0)
        pacing=st.number_input("Pacing per iteration (seconds)",min_value=0.0,value=0.0)
    target_users=st.number_input("Target VUs override (0 = not supplied)",min_value=0,value=0,step=1)
    if st.button("Calculate required VUs",type="primary"):
        result=size_workload(rate if rate>0 else None,scope,response if response>0 else None,
            think if scope=="iteration" else None,pacing if scope=="iteration" else None,
            target_users if target_users>0 else None)
        st.session_state.workload_result=result
    result=st.session_state.get("workload_result")
    if result:
        if result["valid"]: st.metric("Required virtual users",result["required_vus"])
        else:
            for item in result["missing"]: st.warning(item)
            for item in result["errors"]: st.error(item)
        st.code(f"{result['formula']}\n{result['substitution'] or 'Calculation pending'}")
        st.json(result)

elif page=="Compare Runs":
    st.subheader("Compare two performance test runs")
    st.caption("Use comparable test conditions. Differences in workload, environment, and test duration can affect interpretation.")
    uploads=st.file_uploader("Upload baseline and candidate reports",type=["zip","html","htm","csv","jtl","xlsx","xls","json"],accept_multiple_files=True)
    if uploads and st.button("Compare uploaded runs",type="primary",disabled=len(uploads)<2):
        try:
            baseline=parse_upload(uploads[0].name,uploads[0].getvalue()).model_dump()
            candidate=parse_upload(uploads[1].name,uploads[1].getvalue()).model_dump()
            st.session_state.run_comparison=compare_reports(baseline,candidate)
            st.session_state.comparison_names=(uploads[0].name,uploads[1].name)
        except Exception as exc: st.error(f"Comparison failed: {exc}")
    comparison=st.session_state.get("run_comparison")
    if comparison:
        st.write(f"**Baseline:** {st.session_state.comparison_names[0]}  |  **Candidate:** {st.session_state.comparison_names[1]}")
        if comparison["metrics"]: st.dataframe(pd.DataFrame(comparison["metrics"]),use_container_width=True,hide_index=True)
        if comparison["transactions"]: st.dataframe(pd.DataFrame(comparison["transactions"]),use_container_width=True,hide_index=True)
        for warning in comparison["warnings"]: st.warning(warning)
        st.caption("Positive response-time/error deltas generally indicate degradation; positive throughput deltas may be beneficial. Interpret each metric in context.")

elif page=="AI Assistant":
    st.subheader("Evidence-grounded performance assistant")
    if not report_data:
        st.info("Upload a performance report first.")
    else:
        question=st.text_area("Ask about the test or its bottlenecks",placeholder="Why did checkout response time increase?")
        if st.button("Ask PerfAI",type="primary",disabled=not question.strip()):
            try:
                st.markdown(answer_question(question,report_data,st.session_state.get("newrelic_results",[])))
            except OllamaError as exc: st.error(str(exc))
        if st.button("Generate full evidence analysis"):
            try:
                summary=analyze_evidence(report_data,st.session_state.get("findings",[]),st.session_state.get("correlations"))
                st.session_state.ai_summary=summary
                st.markdown(summary)
            except OllamaError as exc: st.error(str(exc))

elif page=="RCA Report":
    st.subheader("Evidence-based RCA export")
    if not report_data:
        st.info("Upload a performance report to generate an RCA.")
    else:
        findings=st.session_state.get("findings",[])
        corr=st.session_state.get("correlations",{})
        ai_summary=st.session_state.get("ai_summary")
        html_report=build_rca_html(report_data,findings,corr,ai_summary)
        st.download_button("Download RCA as HTML",html_report,file_name="perfai-rca.html",mime="text/html")
        st.download_button("Download RCA data as JSON",json_export(report_data,findings,corr),
            file_name="perfai-rca.json",mime="application/json")
        st.download_button("Download RCA as Excel",build_excel(report_data,findings,corr),
            file_name="perfai-rca.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Download RCA as PDF",build_pdf(report_data,findings,corr),
            file_name="perfai-rca.pdf",mime="application/pdf")
        st.caption("The RCA labels observations and hypotheses separately. Validate evidence before declaring root cause.")
        st.components.v1.html(html_report,height=650,scrolling=True)
