from __future__ import annotations
import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

class OllamaError(RuntimeError): pass

def generate(prompt: str, system: str | None=None, model: str=OLLAMA_MODEL) -> str:
    payload={"model":model,"prompt":prompt,"stream":False}
    if system: payload["system"]=system
    try:
        response=requests.post(f"{OLLAMA_BASE_URL}/api/generate",json=payload,timeout=180)
        response.raise_for_status()
        result=response.json().get("response","").strip()
        if not result: raise OllamaError("Ollama returned an empty response.")
        return result
    except requests.RequestException as exc:
        raise OllamaError(f"Cannot reach local Ollama at {OLLAMA_BASE_URL}. Start Ollama and pull {model}. Details: {exc}") from exc
