import pandas as pd
def correlate_timeseries(load_data,apm_data,bucket="10s"):
    if not load_data or not apm_data: return {"aligned":[],"correlations":[],"warnings":["Both time series are required."]}
    frames=[]
    for data in (load_data,apm_data):
        df=pd.DataFrame(data)
        if "timestamp" not in df: return {"aligned":[],"correlations":[],"warnings":["Timestamp field missing."]}
        df["timestamp"]=pd.to_datetime(df["timestamp"],utc=True,errors="coerce")
        df=df.dropna(subset=["timestamp"]).set_index("timestamp").select_dtypes("number").resample(bucket).mean()
        frames.append(df)
    left,right=frames; left.columns=["load_"+str(c) for c in left.columns]; right.columns=["apm_"+str(c) for c in right.columns]
    joined=left.join(right,how="inner"); pairs=[]
    for a in left.columns:
        for b in right.columns:
            p=joined[[a,b]].dropna()
            if len(p)>=3 and p[a].nunique()>1 and p[b].nunique()>1:
                pairs.append({"load_metric":a[5:],"apm_metric":b[4:],"pearson_r":round(float(p[a].corr(p[b])),4),"samples":len(p)})
    return {"aligned":[{"timestamp":i.isoformat(),**r.dropna().to_dict()} for i,r in joined.iterrows()],
      "correlations":sorted(pairs,key=lambda x:abs(x["pearson_r"]),reverse=True),
      "warnings":["Correlation is not causation; verify with traces, logs, and controlled tests."]}
