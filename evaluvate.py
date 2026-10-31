import requests

MODEL = "qwen2.5:1.5b"
URL = "http://localhost:11434/api/generate"

tests = [
    {
        "question": "How many years of experience does Sivahari have?",
        "expected": "3",
    },
    {
        "question": "Which company does Sivahari currently work for?",
        "expected": "Infosys",
    },
    {
        "question": "What degree and field does Sivahari have?",
        "expected": "Computer Science Engineering", 
    },
]

with open("company.txt", encoding="utf-8") as file:
    context = file.read()

passed = 0

for test in tests:
    prompt = f"""Use the resume context below to answer the question with the shortest fact. Do not explain.

Resume:
{context}

Question: {test['question']}
Answer:"""

    response = requests.post(
        URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    answer = response.json()["response"]

    success = test["expected"].lower() in answer.lower()
    passed += success

    print("Question:", test["question"])
    print("Answer:", answer.strip())
    print("PASS" if success else "FAIL")
    print()

print(f"Score: {passed}/{len(tests)}")
