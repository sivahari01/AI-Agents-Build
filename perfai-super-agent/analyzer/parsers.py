import io,json,re,zipfile
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup
from models.schemas import NormalizedReport,TransactionMetric

def parse_jmeter_frame(frame,source="JMeter"):
    if frame.empty: raise ValueError("No sample rows found.")
    cols={str(c).strip().lower().replace(" ","_"):c for c in frame.columns}
    def find(*names):
        return next((cols[n] for n in names if n in cols),None)
    elapsed=find("elapsed","elapsed_time","response_time","latency")
    if elapsed is None: raise ValueError("Missing elapsed/response_time column.")
    label=find("label","sampler","transaction","name"); success=find("success","successful")
    stamp=find("time_stamp","timestamp","time"); thread=find("thread_name","thread")
    df=frame.copy(); df["_ms"]=pd.to_numeric(df[elapsed],errors="coerce"); df=df.dropna(subset=["_ms"])
    if df.empty: raise ValueError("No numeric elapsed-time samples.")
    df["_name"]=df[label].astype(str) if label else "All Samples"
    df["_error"]=~df[success].astype(str).str.lower().isin(["true","1","yes"]) if success else False
    tx=[]
    for name,g in df.groupby("_name"):
        v=g["_ms"]
        tx.append(TransactionMetric(name=str(name),execution_count=len(g),avg_response_time_s=float(v.mean()/1000),
          p90_response_time_s=float(v.quantile(.9)/1000),p95_response_time_s=float(v.quantile(.95)/1000),
          p99_response_time_s=float(v.quantile(.99)/1000),error_count=int(g["_error"].sum()),
          error_pct=float(g["_error"].mean()*100)))
    start=end=duration=None; series=[]
    if stamp:
        dates=pd.to_datetime(df[stamp],unit="ms",utc=True,errors="coerce")
        if dates.notna().any():
            df["_time"]=dates; start=dates.min().isoformat(); end=dates.max().isoformat()
            duration=max((dates.max()-dates.min()).total_seconds(),.001)
            bucket=df.set_index("_time").resample("10s").agg(count=("_ms","count"),avg=("_ms","mean")).dropna()
            series=[{"timestamp":i.isoformat(),"requests":int(r["count"]),"response_time_s":float(r["avg"]/1000)} for i,r in bucket.iterrows()]
    total=len(df); failed=int(df["_error"].sum())
    return NormalizedReport(source=source,scenario_name="JMeter test",started_at=start,ended_at=end,duration_seconds=duration,
      max_virtual_users=int(df[thread].nunique()) if thread else None,total_requests=total,failed_requests=failed,
      error_rate_pct=failed/total*100,average_response_time_s=float(df["_ms"].mean()/1000),
      p90_response_time_s=float(df["_ms"].quantile(.9)/1000),p95_response_time_s=float(df["_ms"].quantile(.95)/1000),
      p99_response_time_s=float(df["_ms"].quantile(.99)/1000),average_tps=total/duration if duration else None,
      transactions=tx,timeseries=series,warnings=["JMeter VU estimate uses distinct thread names; verify against configured threads."])

def parse_upload(filename,data):
    suffix=Path(filename).suffix.lower()
    if suffix in {".csv",".jtl"}: return parse_jmeter_frame(pd.read_csv(io.BytesIO(data)))
    if suffix in {".xlsx",".xls"}: return parse_jmeter_frame(pd.read_excel(io.BytesIO(data)))
    if suffix==".json":
        obj=json.loads(data.decode("utf-8-sig"))
        tx=[TransactionMetric(**x) for x in obj.get("transactions",[])]
        allowed={k:obj.get(k) for k in NormalizedReport.model_fields if k in obj}
        allowed.update(source="JSON",transactions=tx)
        return NormalizedReport(**allowed)
    if suffix in {".html",".htm",".zip"}:
        if suffix==".zip":
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names=[n for n in z.namelist() if n.lower().endswith((".html",".htm"))]
                if not names: raise ValueError("ZIP contains no HTML report.")
                name=next((n for n in names if Path(n).name.lower() in {"index.html","summary.html"}),names[0])
                data=z.read(name)
        soup=BeautifulSoup(data.decode("utf-8",errors="replace"),"html.parser"); text=soup.get_text(" ",strip=True)
        def number(pattern):
            m=re.search(pattern,text,re.I); return float(m.group(1).replace(",","")) if m else None
        return NormalizedReport(source="NeoLoad",scenario_name=filename,
          duration_seconds=number(r"Duration\s*[: ]\s*([\d.]+)\s*(?:s|sec)"),
          max_virtual_users=number(r"(?:Peak|Maximum) virtual users\s*[: ]\s*(\d+)"),
          total_requests=number(r"Total requests\s*[: ]\s*([\d,]+)"),
          average_response_time_s=number(r"Average response time\s*[: ]\s*([\d.]+)"),
          warnings=["HTML parsing is best-effort; confirm metrics against the original NeoLoad report."])
    if suffix in {".log",".txt"}:
        lines=data.decode("utf-8",errors="replace").splitlines()
        errors=[x for x in lines if re.search(r"error|exception|failed",x,re.I)]
        return NormalizedReport(source="Application log",scenario_name=filename,
          warnings=[f"Read {len(lines)} log lines; {len(errors)} error-like lines. Logs do not provide load metrics."])
    raise ValueError(f"Unsupported file type: {suffix}")
