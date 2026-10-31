import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"

with open("company.txt", encoding="utf-8") as file:
    resume = file.read()

print("Local Analyst — type 'exit' to quit")


def ask(question):
    prompt = f"""Answer using only this resume:

{resume}

Question: {question}
"""

    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"]


while True:
    question = input("\nYou: ").strip()

    if question.lower() in ("exit", "quit"):
        break

    if question:
        print("Analyst:", ask(question))