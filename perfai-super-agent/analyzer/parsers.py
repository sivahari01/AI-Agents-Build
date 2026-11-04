from __future__ import annotations
import csv, io, json, re, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
from bs4 import BeautifulSoup
from models.schemas import NormalizedReport, TransactionMetric

def _num(value: Any) -> float | None:
    if value is None or str(value).strip() in {"", "-", "N/A", "None"}: return None
    try: return float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError): return None

def _first(mapping: dict, *keys):
    lower={str(k).lower().replace(" ","_"):v for k,v in mapping.items()}
    for key in keys:
        if key in lower and lower[key] not in (None,""): return lower[key]
    return None

def parse_jmeter_frame(frame: pd.DataFrame, source="JMeter") -> NormalizedReport:
    if frame.empty: raise ValueError("The JMeter file contains no sample rows.")
    cols={str(c).strip().lower().replace(" ","_"):c for c in frame.columns}
    def col(*names):
        for n in names:
            if n in cols: return cols[n]
        return None
    elapsed=col("elapsed","elapsed_time","response_time","latency")
    label=col("label","sampler","transaction","name")
    success=col("success","successful")
    timestamp=col("time_stamp","timestamp","time")
    thread=col("thread_name","thread")
    if elapsed is None: raise ValueError("No elapsed/response-time column found. Export JMeter results as CSV/JTL.")
    frame=frame.copy()
    frame["_elapsed_ms"]=pd.to_numeric(frame[elapsed],errors="coerce")
    frame=frame.dropna(subset=["_elapsed_ms"])
    if frame.empty: raise ValueError("No numeric elapsed-time samples were found.")
    frame["_label"]=frame[label].astype(str) if label else "All Samples"
    frame["_error"]=False
    if success:
        frame["_error"]=~frame[success].astype(str).str.lower().isin(["true","1","yes"])
    grouped=frame.groupby("_label",dropna=False)
    tx=[]
    for name,g in grouped:
        ms=g["_elapsed_ms"]
        tx.append(TransactionMetric(name=str(name),execution_count=len(g),
            avg_response_time_s=float(ms.mean()/1000),p90_response_time_s=float(ms.quantile(.90)/1000),
            p95_response_time_s=float(ms.quantile(.95)/1000),p99_response_time_s=float(ms.quantile(.99)/1000),
            error_count=int(g["_error"].sum()),error_pct=float(g["_error"].mean()*100)))
    start=end=None; duration=None; ts=[]
    if timestamp:
        dates=pd.to_datetime(frame[timestamp],unit="ms",errors="coerce",utc=True)
        if not dates.notna().any():
            dates=pd.to_datetime(frame[timestamp],errors="coerce",utc=True)
        if dates.notna().any():
            frame["_time"]=dates
            start=dates.min().isoformat(); end=dates.max().isoformat()
            span=(dates.max()-dates.min()).total_seconds()
            duration=span if span>0 else None
            bucket=frame.set_index("_time").resample("10s").agg(samples=("_elapsed_ms","count"),avg_ms=("_elapsed_ms","mean"),errors=("_error","sum")).dropna(how="all")
            ts=[{"timestamp":idx.isoformat(),"requests":int(r.samples),"response_time_s":float(r.avg_ms/1000),"errors":int(r.errors)} for idx,r in bucket.iterrows()]
    total=len(frame); failed=int(frame["_error"].sum())
    distinct_threads=int(frame[thread].nunique()) if thread else None
    return NormalizedReport(source=source,scenario_name="JMeter test",started_at=start,ended_at=end,
        duration_seconds=duration,max_virtual_users=None,total_requests=total,failed_requests=failed,
        error_rate_pct=failed/total*100 if total else None,average_response_time_s=float(frame["_elapsed_ms"].mean()/1000),
        p90_response_time_s=float(frame["_elapsed_ms"].quantile(.90)/1000),
        p95_response_time_s=float(frame["_elapsed_ms"].quantile(.95)/1000),
        p99_response_time_s=float(frame["_elapsed_ms"].quantile(.99)/1000),
        average_rps=total/duration if duration and duration>0 else None,transactions=tx,timeseries=ts,
        warnings=["Concurrent VUs are not inferred from total distinct JMeter thread names.",
                  "Test duration and throughput are unavailable when usable timestamps are absent."] ,
        raw_metadata={"distinct_thread_names":distinct_threads})

def parse_json_report(data: bytes, filename="report.json") -> NormalizedReport:
    obj=json.loads(data.decode("utf-8-sig"))
    if isinstance(obj,list): obj={"samples":obj}
    # Prometheus range-query JSON export: preserve each metric series as its own numeric column.
    prom=obj.get("data",{}) if isinstance(obj,dict) else {}
    if obj.get("status")=="success" and isinstance(prom.get("result"),list):
        buckets={}
        for series in prom["result"]:
            labels=series.get("metric",{})
            metric_name=labels.get("__name__") or labels.get("job") or labels.get("instance") or "prometheus_value"
            safe_name=re.sub(r"[^A-Za-z0-9_]+","_",str(metric_name)).strip("_") or "prometheus_value"
            for point in series.get("values",[]):
                if len(point)<2: continue
                try:
                    stamp=datetime.fromtimestamp(float(point[0]),tz=timezone.utc).isoformat()
                    buckets.setdefault(stamp,{"timestamp":stamp})[safe_name]=_num(point[1])
                except (ValueError,TypeError,OverflowError): continue
        rows=sorted(buckets.values(),key=lambda x:x["timestamp"])
        return NormalizedReport(source="Prometheus JSON",scenario_name=filename,timeseries=rows,
            warnings=["Prometheus range-query data contains infrastructure telemetry, not load-test transactions."])
    txraw=obj.get("transactions",[])
    tx=[]
    for row in txraw if isinstance(txraw,list) else []:
        tx.append(TransactionMetric(name=str(row.get("name","Unknown")),
            execution_count=_num(row.get("execution_count")),avg_response_time_s=_num(row.get("avg_response_time_s")),
            p90_response_time_s=_num(row.get("p90_response_time_s")),p95_response_time_s=_num(row.get("p95_response_time_s")),
            p99_response_time_s=_num(row.get("p99_response_time_s")),error_count=_num(row.get("error_count")),
            error_pct=_num(row.get("error_pct"))))
    return NormalizedReport(source="JSON",scenario_name=obj.get("scenario_name") or filename,
        started_at=obj.get("started_at"),ended_at=obj.get("ended_at"),duration_seconds=_num(obj.get("duration_seconds")),
        max_virtual_users=_num(obj.get("max_virtual_users") or obj.get("peak_vus")),
        total_requests=_num(obj.get("total_requests")),failed_requests=_num(obj.get("failed_requests") or obj.get("failed_transactions")),
        error_rate_pct=_num(obj.get("error_rate_pct") or obj.get("error_pct")),
        average_response_time_s=_num(obj.get("average_response_time_s")),
        p90_response_time_s=_num(obj.get("p90_response_time_s")),p95_response_time_s=_num(obj.get("p95_response_time_s")),
        p99_response_time_s=_num(obj.get("p99_response_time_s")),average_tps=_num(obj.get("average_tps") or obj.get("transaction_tps")),
        average_rps=_num(obj.get("average_rps") or obj.get("rps")),iteration_ips=_num(obj.get("iteration_ips")),
        iteration_average_time_s=_num(obj.get("iteration_average_time_s")),transactions=tx,
        timeseries=obj.get("timeseries",[]) if isinstance(obj.get("timeseries",[]),list) else [],
        raw_metadata={"input_filename":filename})

def parse_neoload_html(html: str, source_name="NeoLoad HTML") -> NormalizedReport:
    soup=BeautifulSoup(html,"html.parser")
    text=soup.get_text(" ",strip=True)
    def find(pattern):
        m=re.search(pattern,text,re.I)
        return m.group(1).strip() if m else None
    duration=_num(find(r"(?:Duration|Test duration)\s*[: ]\s*([\d.]+)\s*(?:s|sec|seconds)"))
    users=_num(find(r"(?:Maximum virtual users|Peak virtual users|Virtual users)\s*[: ]\s*(\d+)"))
    reqs=_num(find(r"(?:Total requests|Requests)\s*[: ]\s*([\d,]+)"))
    failed=_num(find(r"(?:Failed requests|Errors)\s*[: ]\s*([\d,]+)"))
    avg=_num(find(r"(?:Average response time|Avg response time)\s*[: ]\s*([\d.]+)\s*(?:s|sec)?"))
    tx=[]
    for table in soup.find_all("table"):
        rows=table.find_all("tr")
        if len(rows)<2: continue
        headers=[c.get_text(" ",strip=True).lower() for c in rows[0].find_all(["th","td"])]
        if not any("transaction" in h or h in {"name","path"} for h in headers): continue
        for tr in rows[1:]:
            vals=[c.get_text(" ",strip=True) for c in tr.find_all(["td","th"])]
            if len(vals)!=len(headers): continue
            d=dict(zip(headers,vals))
            name=next((d[h] for h in headers if "transaction" in h or h in {"name","path"}),None)
            if not name: continue
            def pick(part): return next((v for k,v in d.items() if part in k),None)
            tx.append(TransactionMetric(name=name,execution_count=_num(pick("count") or pick("execut")),
                avg_response_time_s=_num(pick("average") or pick("avg")),
                p95_response_time_s=_num(pick("95")),p99_response_time_s=_num(pick("99")),
                error_count=_num(pick("error")),error_pct=_num(pick("error %"))))
    warnings=["NeoLoad HTML extraction is best-effort. Validate values against the report; upload the full ZIP for richer parsing."]
    return NormalizedReport(source="NeoLoad",scenario_name=find(r"(?:Scenario)\s*[: ]\s*([\w -]+)") or source_name,
        duration_seconds=duration,max_virtual_users=int(users) if users is not None else None,
        total_requests=int(reqs) if reqs is not None else None,failed_requests=int(failed) if failed is not None else None,
        error_rate_pct=(failed/reqs*100 if failed is not None and reqs else None),
        average_response_time_s=avg,transactions=tx,warnings=warnings)

def parse_upload(filename: str, data: bytes) -> NormalizedReport:
    suffix=Path(filename).suffix.lower()
    if suffix in {".csv",".jtl"}:
        return parse_jmeter_frame(pd.read_csv(io.BytesIO(data)))
    if suffix in {".xlsx",".xls"}:
        return parse_jmeter_frame(pd.read_excel(io.BytesIO(data)))
    if suffix==".json": return parse_json_report(data,filename)
    if suffix in {".html",".htm"}: return parse_neoload_html(data.decode("utf-8",errors="replace"),filename)
    if suffix==".zip":
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            candidates=[n for n in zf.namelist() if n.lower().endswith((".html",".htm")) and not n.endswith("/")]
            if not candidates: raise ValueError("ZIP contains no HTML report.")
            preferred=next((n for n in candidates if Path(n).name.lower()=="summary.html"),None) or next((n for n in candidates if Path(n).name.lower()=="index.html"),candidates[0])
            return parse_neoload_html(zf.read(preferred).decode("utf-8",errors="replace"),preferred)
    if suffix in {".log",".txt"}:
        lines=data.decode("utf-8",errors="replace").splitlines()
        err=[line for line in lines if re.search(r"\b(error|exception|failed)\b",line,re.I)]
        return NormalizedReport(source="Application log",scenario_name=filename,
            warnings=[f"Parsed {len(lines)} lines; found {len(err)} error-like lines. Logs alone do not provide load-test metrics."],
            raw_metadata={"line_count":len(lines),"error_samples":err[:100]})
    raise ValueError(f"Unsupported file type: {suffix}")
