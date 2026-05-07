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

content = "Subject: \nFrom: \n\nBody:\n"

payload = {
    "model": "gemma4:e4b",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ],
    "stream": False
}

try:
    response = requests.post(OLLAMA_URL, json=payload, timeout=30)
    result = response.json()
    message_content = result.get("message", {}).get("content", "{}").strip()
    print("CONTENT:", repr(message_content))
    if message_content.startswith("```json"):
        message_content = message_content[7:]
    if message_content.endswith("```"):
        message_content = message_content[:-3]
    print("STRIPPED:", repr(message_content.strip()))
    parsed = json.loads(message_content.strip())
    print("PARSED:", parsed)
except Exception as e:
    import traceback
    traceback.print_exc()
