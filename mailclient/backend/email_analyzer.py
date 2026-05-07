# Proyecto NinjaSpam - Entrega 1
# Analizador técnico de cabeceras de seguridad

def calculate_header_score(headers: list[dict]) -> dict:
    """
    Calcula una calificación básica sobre 10 basada en los metadatos y cabeceras del correo.
    Devuelve un diccionario con 'score' y la lista de 'details' de lo que evaluó.
    """
    score = 5.0  # Calificación base (empieza a la mitad)
    details = []

    header_dict = {h["name"].lower(): h["value"].lower() for h in headers}
    
    # 1. Autenticación (SPF, DKIM, DMARC)
    auth_results = header_dict.get("authentication-results", "")
    spf_header = header_dict.get("received-spf", "")
    dkim_header = header_dict.get("dkim-signature", "")
    
    has_spf = "spf=pass" in auth_results or "pass" in spf_header
    has_dkim = "dkim=pass" in auth_results or bool(dkim_header)
    has_dmarc = "dmarc=pass" in auth_results
    
    if has_spf:
        score += 1.5
        details.append({"rule": "SPF Pass", "points": 1.5, "desc": "El remitente está autorizado para enviar correos desde este dominio."})
    else:
        score -= 1.0
        details.append({"rule": "SPF Faltante/Fallido", "points": -1.0, "desc": "No se encontró un registro SPF válido."})

    if has_dkim:
        score += 1.5
        details.append({"rule": "Firma DKIM", "points": 1.5, "desc": "El correo contiene una firma criptográfica DKIM válida."})
    else:
        score -= 0.5
        details.append({"rule": "Sin DKIM", "points": -0.5, "desc": "El correo no está firmado por DKIM."})
        
    if has_dmarc:
        score += 1.0
        details.append({"rule": "DMARC Pass", "points": 1.0, "desc": "El dominio tiene una política DMARC válida de seguridad."})

    # 2. Calificaciones previas de SpamAssassin (si existen)
    spam_score_header = header_dict.get("x-spam-score", "0")
    try:
        spam_score = float(spam_score_header)
        if spam_score < 0:
            score += 1.0
            details.append({"rule": "Buen puntaje de SpamAssassin", "points": 1.0, "desc": f"El puntaje previo es negativo ({spam_score})."})
        elif spam_score > 2:
            score -= 2.0
            details.append({"rule": "Mal puntaje de SpamAssassin", "points": -2.0, "desc": f"El puntaje previo es muy alto ({spam_score})."})
    except ValueError:
        pass

    # 3. Estructura del ID del mensaje y fechas
    if "message-id" in header_dict:
        score += 0.5
        details.append({"rule": "Message-ID válido", "points": 0.5, "desc": "Se proporcionó un Message-ID correcto."})
    else:
        score -= 1.0
        details.append({"rule": "Sin Message-ID", "points": -1.0, "desc": "Falta la cabecera Message-ID."})
        
    if "list-unsubscribe" in header_dict:
        score += 0.5
        details.append({"rule": "List-Unsubscribe", "points": 0.5, "desc": "Contiene un enlace correcto para darse de baja."})

    # Aseguramos que la calificación no se salga de los límites 0-10
    final_score = max(0.0, min(10.0, score))
    
    return {
        "score": round(final_score, 1),
        "details": details
    }
