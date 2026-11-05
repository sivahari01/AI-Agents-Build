import json
import pandas as pd
import plotly.express as px
import streamlit as st
from analyzer.parsers import parse_upload
from analyzer.bottlenecks import detect_bottlenecks
from analyzer.workload import size_workload
from integrations.newrelic import NewRelicClient, NewRelicError
from config import NEW_RELIC_API_KEY, NEW_RELIC_ACCOUNT_ID, NEW_RELIC_REGION

st.set_page_config(page_title="PerfAI | Performance Intelligence",page_icon="📈",layout="wide")
st.title("PerfAI — Super Performance Intelligence Agent")
st.caption("Evidence-led load-test analysis with optional New Relic telemetry and local AI.")
if "report" not in st.session_state: st.session_state.report=None
pages=["Executive Dashboard","Report Analyzer","New Relic Integration","Workload Model","RCA Findings"]
page=st.sidebar.radio("Workspace",pages)

if page in ("Executive Dashboard","Report Analyzer"):
    uploaded=st.file_uploader("Upload NeoLoad ZIP/HTML, JMeter CSV/JTL, Excel, JSON, or application log",type=["zip","html","htm","csv","jtl","xlsx","xls","json","log","txt"])
    if uploaded and st.button("Parse report"):
        try:
            st.session_state.report=parse_upload(uploaded.name,uploaded.getvalue()).model_dump()
            st.success("Report parsed. Verify extracted fields against the source report.")
        except Exception as e: st.error(str(e))
    r=st.session_state.report
    if r:
        a,b,c,d=st.columns(4)
        a.metric("Requests",r.get("total_requests") if r.get("total_requests") is not None else "N/A")
        b.metric("Average RT",f"{r['average_response_time_s']:.3f}s" if r.get("average_response_time_s") is not None else "N/A")
        c.metric("Error rate",f"{r['error_rate_pct']:.2f}%" if r.get("error_rate_pct") is not None else "N/A")
        d.metric("Peak VUs",r.get("max_virtual_users") if r.get("max_virtual_users") is not None else "N/A")
        st.subheader("Transaction metrics")
        st.dataframe(pd.DataFrame(r.get("transactions",[]")),use_container_width=True)
        if r.get("timeseries"):
            df=pd.DataFrame(r["timeseries"])
            if "timestamp" in df and "response_time_s" in df:
                st.plotly_chart(px.line(df,x="timestamp",y="response_time_s",title="Response time over time"),use_container_width=True)
        st.download_button("Download normalized JSON",json.dumps(r,indent=2),"perfai-normalized-report.json")
    else: st.info("Upload a performance report to begin.")

elif page=="New Relic Integration":
    st.subheader("Read-only New Relic connection")
    key=st.text_input("User API key",value=NEW_RELIC_API_KEY,type="password")
    account=st.text_input("Account ID",value=str(NEW_RELIC_ACCOUNT_ID))
    region=st.selectbox("Region",["US","EU"],index=0 if NEW_RELIC_REGION!="EU" else 1)
    if st.button("Test connection"):
        try: st.success(NewRelicClient(key,account,region).test_connection())
        except NewRelicError as e: st.error(str(e))
    entity_name=st.text_input("Search entity name")
    if st.button("Discover entities"):
        try: st.json(NewRelicClient(key,account,region).discover_entities(entity_name))
        except NewRelicError as e: st.error(str(e))
    nrql=st.text_area("NRQL (read-only SELECT)",'SELECT average(duration) FROM Transaction SINCE 30 minutes ago TIMESERIES')
    if st.button("Run NRQL"):
        try: st.dataframe(pd.DataFrame(NewRelicClient(key,account,region).run_nrql(nrql)),use_container_width=True)
        except NewRelicError as e: st.error(str(e))

elif page=="Workload Model":
    scope=st.selectbox("Sizing scope",["transaction","iteration"])
    rate=st.number_input("Target transaction TPS / iteration IPS",min_value=0.0,value=10.0)
    rt=st.number_input("Average response time (seconds)",min_value=0.0,value=1.0)
    think=st.number_input("Total think time per iteration (seconds)",min_value=0.0,value=0.0)
    pacing=st.number_input("Pacing per iteration (seconds)",min_value=0.0,value=0.0)
    if st.button("Calculate VUs"):
        result=size_workload(rate,scope,rt,think,pacing)
        st.json(result)
        if result["valid"]: st.metric("Required VUs",result["required_vus"])
elif page=="RCA Findings":
    r=st.session_state.report
    if not r: st.info("Parse a report first.")
    else:
        metrics={"error_rate_pct":r.get("error_rate_pct"),"response_time_s":r.get("average_response_time_s")}
        st.json(detect_bottlenecks(metrics))
        st.caption("Rule findings are indicators, not proof of root cause.")
