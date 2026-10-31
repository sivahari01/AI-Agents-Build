import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen2.5:1.5b",
        "prompt": "Write a short story about a robot learning to love.",
        "stream": False,
    },
    timeout=120,
)
response.raise_for_status()
print(response.json()["response"])
