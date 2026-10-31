import requests


def calculate(expression):
    try:
        allowed = set("0123456789+-*/(). ")
        if not set(expression) <= allowed:
            return "Invalid expression"

        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as error:
        return f"Error: {error}"


question = input("Question: ")

if "calculate" in question.lower():
    expression = question.lower().replace("calculate", "").strip()
    result = calculate(expression)
else:
    result = None

prompt = question
if result is not None:
    prompt = f"Question: {question}\nTool result: {result}\nAnswer briefly."

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen2.5:1.5b",
        "prompt": prompt,
        "stream": False,
    },
    timeout=120,
)
response.raise_for_status()
print(response.json()["response"])