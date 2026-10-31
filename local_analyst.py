import faiss  # type: ignore[import-not-found]
import json
import requests
import urllib.request
from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"

with open("company.txt", encoding="utf-8") as file:
    chunks = [line.strip() for line in file.read().splitlines() if line.strip()]

embedder = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = embedder.encode(chunks)
index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

history = []


def calculate(expression):
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        return "Invalid expression"

    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as error:
        return f"Error: {error}"


while True:
    question = input("\nQuestion: ").strip()

    if question.lower() in ("exit", "quit"):
        break

    if "calculate" in question.lower():
        expression = question.lower().replace("calculate", "").strip()
        answer = calculate(expression)
        print("Answer:", answer)
        continue

    query_vector = embedder.encode([question])
    result_count = min(5, len(chunks))
    _, indices = index.search(query_vector, result_count)
    context = "\n".join(chunks[i] for i in indices[0])

    history_text = "\n".join(history[-6:])
    prompt = f"""Answer using only the context and conversation.

Context:
{context}

Conversation:
{history_text}

Question:
{question}
"""

    response = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "prompt": prompt, "stream": False},
        timeout=120,
    )
    response.raise_for_status()

    answer = response.json()["response"]
    print("Answer:", answer)
    history.append(f"User: {question}")
    history.append(f"Assistant: {answer}")