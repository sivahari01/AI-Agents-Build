import requests

MODEL = "qwen2.5:1.5b"
URL = "http://localhost:11434/api/generate"
history = []

while True:
    prompt = input("You: ").strip()

    if prompt.lower() in ("exit", "quit"):
        break

    history.append({"role": "user", "content": prompt})
    messages = "\n".join(
        f"{message['role']}: {message['content']}"
        for message in history
    )

    response = requests.post(
        URL,
        json={
            "model": MODEL,
            "prompt": messages,
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()

    answer = response.json()["response"]
    print("AI:", answer)

    history.append({"role": "assistant", "content": answer})
