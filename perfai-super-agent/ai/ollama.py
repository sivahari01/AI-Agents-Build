"""Optional local Ollama client."""
from __future__ import annotations
import requests

class OllamaError(RuntimeError): pass

class OllamaClient:
 def __init__(self,base_url:str,model:str,timeout:int=120):
  self.base_url=base_url.rstrip("/"); self.model=model; self.timeout=timeout
 def health(self)->bool:
  try:
   response=requests.get(f"{self.base_url}/api/tags",timeout=5); response.raise_for_status(); return True
  except requests.RequestException: return False
 def explain(self,system_prompt:str,user_prompt:str)->str:
  try:
   response=requests.post(f"{self.base_url}/api/generate",
    json={"model":self.model,"system":system_prompt,"prompt":user_prompt,"stream":False,
          "options":{"temperature":0.2,"num_predict":900}},timeout=self.timeout)
   response.raise_for_status()
   result=response.json().get("response","").strip()
   if not result: raise OllamaError("Ollama returned an empty response")
   return result
  except requests.RequestException as exc:
   raise OllamaError(f"Local Ollama is unavailable: {exc}") from exc

SYSTEM_PROMPT="""You are PerfAI, a senior performance engineering analyst.
Use only supplied evidence. Never invent telemetry or metrics.
Separate measured observations, temporal correlations, hypotheses, and confirmed causes.
Correlation is not causation. Identify missing evidence and suggest next investigations."""

def build_analysis_prompt(report:dict,findings:dict,correlations:list[dict])->str:
 import json
 context={"performance_report":report,"bottleneck_analysis":findings,"time_series_correlations":correlations}
 return "Analyze this performance evidence and produce an RCA draft.\n"+json.dumps(context,default=str,ensure_ascii=False)
