from openai import OpenAI
from dotenv import load_dotenv
import os

# Load configuration
load_dotenv()

# Create AI client
client = OpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY")
)

print("=" * 40)
print("      My AI Assistant")
print("=" * 40)
userMessages = []
while True:

    user_input = input("\nYou : ")
    userMessages.append({"role": "user", "content": user_input})
    if user_input.lower().strip() == "quit":
        print("\nAI  : Goodbye! Have a great day.")
        break

    try:
        response = client.chat.completions.create(
            model=os.getenv("MODEL"),
            messages=userMessages
        )
    except KeyboardInterrupt:
        print("\nAI  : Response cancelled.")
        userMessages.pop()
        continue
    except Exception as error:
        print(f"\nAI  : Error connecting to the model: {error}")
        userMessages.pop()
        continue
    ai_reply = response.choices[0].message.content
    userMessages.append({"role": "assistant", "content": ai_reply})
    print("\nAI :", ai_reply)
    print("=" * 40)
    for msg in userMessages:
        print(f"{msg['role'].capitalize()} : {msg['content']}")
