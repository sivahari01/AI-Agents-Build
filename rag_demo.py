import faiss
import requests
from sentence_transformers import SentenceTransformer

with open("company.txt", encoding="utf-8") as file:
    text = file.read()

chunks = [line.strip() for line in text.splitlines() if line.strip()]

embedder = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = embedder.encode(chunks)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

query = input("Question: ")
query_vector = embedder.encode([query])
result_count = min(5, len(chunks))
_, indices = index.search(query_vector, result_count)
context = "\n".join(chunks[i] for i in indices[0])

prompt = f"""Answer using only this context:

Context:
{context}

Question: {query}
"""

response = requests.post(
    "http://localhost:11434/api/generate",
    json={"model": "qwen2.5:1.5b", "prompt": prompt, "stream": False},
    timeout=120,
)
response.raise_for_status()
print(response.json()["response"])