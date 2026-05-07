import requests
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL = "gemma4:e4b"

# Proyecto NinjaSpam - Entrega 1
# Servicio de conexión con la Inteligencia Artificial (Ollama)

def analyze_spam_with_ai(email_detail: dict) -> dict:
    """
    Toma los detalles del correo y los envía a la API de Ollama
    para analizar la probabilidad de que sea spam.
    """
    subject = email_detail.get("subject", "")
    from_addr = ", ".join(email_detail.get("from", []))
    body = email_detail.get("body", {}).get("preferred", "")
    
    # Truncamos el cuerpo para no saturar la ventana de contexto del modelo local
    if len(body) > 1500:
        body = body[:1500] + "\n...[TRUNCATED]"
        
    content = f"Subject: {subject}\nFrom: {from_addr}\n\nBody:\n{body}"
    
    # Le decimos a la IA cómo debe comportarse
    system_prompt = (
        "You are an expert spam filter. Analyze the following email content. "
        "Reply strictly with a JSON object containing two keys: "
        "'spam_probability' (a number between 0 and 100) and 'reason' (a brief explanation in Spanish)."
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
        
        # Buscamos el bloque JSON ignorando cualquier texto conversacional de la IA
        message_content = result.get("message", {}).get("content", "{}").strip()
        match = re.search(r'\{.*\}', message_content, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError:
                parsed_data = {"spam_probability": 80, "reason": "El correo es tan sospechoso que confundió a la IA y rompió su formato de respuesta."}
        else:
            # Si el modelo decidió responder con puro texto y sin JSON
            parsed_data = {
                "spam_probability": 75,
                "reason": f"La IA analizó el texto pero no devolvió un formato válido. Su respuesta fue: {message_content[:150]}..."
            }

        return {
            "success": True,
            "spam_probability": parsed_data.get("spam_probability", 50),
            "reason": parsed_data.get("reason", "Análisis completado sin comentarios adicionales.")
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Falla al conectar con el servicio de IA: {str(e)}"
        }
