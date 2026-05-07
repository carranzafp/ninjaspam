import requests
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

system_prompt = (
    "You are an expert spam filter. Analyze the following email content. "
    "Reply strictly with a JSON object containing two keys: "
    "'spam_probability' (a number between 0 and 100) and 'reason' (a brief explanation in Spanish)."
)

# Read the massive content from a file
with open("huge_email.txt", "r", encoding="utf-8") as f:
    content = f.read()

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
    print("STATUS:", response.status_code)
    result = response.json()
    message_content = result.get("message", {}).get("content", "{}").strip()
    print("RAW CONTENT:", repr(message_content))
    match = re.search(r'\{.*\}', message_content, re.DOTALL)
    if match:
        json_str = match.group(0)
    else:
        json_str = message_content

    parsed = json.loads(json_str)
    print("PARSED:", parsed)
except Exception as e:
    import traceback
    traceback.print_exc()
