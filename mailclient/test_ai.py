import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

system_prompt = (
    "You are an expert spam filter. Analyze the following email content. "
    "Reply strictly with a JSON object containing two keys: "
    "'spam_probability' (a number between 0 and 100) and 'reason' (a brief explanation in Spanish)."
)

content = "Subject: Prueba de spam !!\nFrom: test@test.com\n\nBody:\nHola, esto es una prueba."

payload = {
    "model": "gemma4:e4b",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ],
    "stream": False
}

print("URL:", OLLAMA_URL)
try:
    response = requests.post(OLLAMA_URL, json=payload, timeout=30)
    print("STATUS:", response.status_code)
    print("RAW TEXT:", repr(response.text))
    result = response.json()
    print("JSON RESULT:", result)
    message_content = result.get("message", {}).get("content", "{}").strip()
    print("CONTENT:", repr(message_content))
    if message_content.startswith("```json"):
        message_content = message_content[7:]
    if message_content.endswith("```"):
        message_content = message_content[:-3]
    parsed = json.loads(message_content)
    print("PARSED:", parsed)
except Exception as e:
    import traceback
    traceback.print_exc()
