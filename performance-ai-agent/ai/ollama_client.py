"""Small direct client for the local Ollama HTTP API."""

from __future__ import annotations

import json

import requests


class OllamaUnavailableError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        model: str = "qwen2.5:0.5b",
        base_url: str = "http://127.0.0.1:11434",
        keep_alive: str = "5m",
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.keep_alive = keep_alive

    def health(self) -> dict:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise OllamaUnavailableError(
                "Ollama is not reachable. Start it with `ollama serve`."
            ) from exc

    def generate(self, prompt: str, system: str | None = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": {"num_predict": 512},
        }
        if system:
            payload["system"] = system
        try:
            response = requests.post(
                f"{self.base_url}/api/generate", json=payload, timeout=120
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.RequestException as exc:
            raise OllamaUnavailableError(f"Ollama could not generate an answer: {exc}") from exc
