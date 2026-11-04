from __future__ import annotations
import pandas as pd

def correlate_timeseries(load_data: list[dict], apm_data: list[dict], bucket="10s") -> dict:
    """Align two timestamped series and calculate Pearson correlations.

    Inputs use timestamp plus numeric fields. Results describe association only.
    """
    if not load_data or not apm_data:
        return {"aligned":[],"correlations":[],"warnings":["Both load-test and APM time series are required."]}
    left=pd.DataFrame(load_data).copy(); right=pd.DataFrame(apm_data).copy()
    for frame in (left,right):
        if "timestamp" not in frame: return {"aligned":[],"correlations":[],"warnings":["A timestamp field is missing."]}
        frame["timestamp"]=pd.to_datetime(frame["timestamp"],utc=True,errors="coerce")
        frame.dropna(subset=["timestamp"],inplace=True)
        frame.sort_values("timestamp",inplace=True)
        frame.set_index("timestamp",inplace=True)
    left=left.select_dtypes("number").resample(bucket).mean()
    right=right.select_dtypes("number").resample(bucket).mean()
    left.columns=[f"load_{c}" for c in left.columns]
    right.columns=[f"apm_{c}" for c in right.columns]
    joined=left.join(right,how="inner").dropna(how="all")
    pairs=[]
    for lcol in left.columns:
        for rcol in right.columns:
            pair=joined[[lcol,rcol]].dropna()
            if len(pair)>=3 and pair[lcol].nunique()>1 and pair[rcol].nunique()>1:
                pairs.append({"load_metric":lcol.removeprefix("load_"),"apm_metric":rcol.removeprefix("apm_"),
                              "pearson_r":round(float(pair[lcol].corr(pair[rcol])),4),"samples":len(pair)})
    return {"aligned":[{"timestamp":i.isoformat(),**{k:(float(v) if pd.notna(v) else None) for k,v in row.items()}} for i,row in joined.iterrows()],
            "correlations":sorted(pairs,key=lambda x:abs(x["pearson_r"]),reverse=True),
            "warnings":["Correlation is not causation. Confirm hypotheses with traces, logs, profiles, and controlled tests.",
                        "Only overlapping timestamps and numeric columns are compared."]}
