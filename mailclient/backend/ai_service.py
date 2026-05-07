import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL = "gemma4:e4b"

def analyze_spam_with_ai(email_detail: dict) -> dict:
    """
    Sends email details to the Ollama API to analyze spam probability.
    """
    subject = email_detail.get("subject", "")
    from_addr = ", ".join(email_detail.get("from", []))
    body = email_detail.get("body", {}).get("preferred", "")
    
    content = f"Subject: {subject}\nFrom: {from_addr}\n\nBody:\n{body}"
    
    system_prompt = (
        "You are an expert spam filter. Analyze the following email content. "
        "Reply strictly with a JSON object containing two keys: "
        "'spam_probability' (a number between 0 and 100) and 'reason' (a brief explanation)."
    )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ],
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # Try to parse the response as JSON. Models sometimes add markdown formatting.
        message_content = result.get("message", {}).get("content", "{}").strip()
        if message_content.startswith("```json"):
            message_content = message_content[7:]
        if message_content.endswith("```"):
            message_content = message_content[:-3]
            
        parsed_data = json.loads(message_content)
        return {
            "success": True,
            "spam_probability": parsed_data.get("spam_probability", 50),
            "reason": parsed_data.get("reason", "Analysis complete.")
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to reach AI service: {str(e)}"
        }
