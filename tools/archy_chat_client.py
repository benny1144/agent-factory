import requests
import json

def chat_with_archy(message: str):
    url = "http://localhost:5065/chat"
    payload = {"message": message}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print(f"Archy: {response.json()['reply']}")
        else:
            print(f"[Error] {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[Exception] {e}")

if __name__ == "__main__":
    print("🜂 Archy Chat Client 🜂")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            print("Goodbye.")
            break
        chat_with_archy(user_input)
