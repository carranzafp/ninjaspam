def calculate_header_score(headers: list[dict]) -> dict:
    """
    Calculates a basic score out of 10 based on email headers.
    Returns a dict with 'score' and 'details' array.
    """
    score = 5.0  # Base score
    details = []

    header_dict = {h["name"].lower(): h["value"].lower() for h in headers}
    
    # 1. Authentication (SPF, DKIM, DMARC)
    auth_results = header_dict.get("authentication-results", "")
    spf_header = header_dict.get("received-spf", "")
    dkim_header = header_dict.get("dkim-signature", "")
    
    has_spf = "spf=pass" in auth_results or "pass" in spf_header
    has_dkim = "dkim=pass" in auth_results or bool(dkim_header)
    has_dmarc = "dmarc=pass" in auth_results
    
    if has_spf:
        score += 1.5
        details.append({"rule": "SPF Pass", "points": 1.5, "desc": "Sender is authorized to send emails for this domain."})
    else:
        score -= 1.0
        details.append({"rule": "SPF Missing/Fail", "points": -1.0, "desc": "No valid SPF record found."})

    if has_dkim:
        score += 1.5
        details.append({"rule": "DKIM Signature", "points": 1.5, "desc": "Email contains a valid DKIM signature."})
    else:
        score -= 0.5
        details.append({"rule": "No DKIM", "points": -0.5, "desc": "Email does not have a DKIM signature."})
        
    if has_dmarc:
        score += 1.0
        details.append({"rule": "DMARC Pass", "points": 1.0, "desc": "Domain has a valid DMARC policy."})

    # 2. Existing SpamAssassin Scores
    spam_score_header = header_dict.get("x-spam-score", "0")
    try:
        spam_score = float(spam_score_header)
        if spam_score < 0:
            score += 1.0
            details.append({"rule": "Good SpamAssassin Score", "points": 1.0, "desc": f"Score is negative ({spam_score})."})
        elif spam_score > 2:
            score -= 2.0
            details.append({"rule": "Poor SpamAssassin Score", "points": -2.0, "desc": f"Score is high ({spam_score})."})
    except ValueError:
        pass

    # 3. Message ID and Date structure
    if "message-id" in header_dict:
        score += 0.5
        details.append({"rule": "Valid Message-ID", "points": 0.5, "desc": "A proper Message-ID was provided."})
    else:
        score -= 1.0
        details.append({"rule": "No Message-ID", "points": -1.0, "desc": "Missing Message-ID header."})
        
    if "list-unsubscribe" in header_dict:
        score += 0.5
        details.append({"rule": "List-Unsubscribe", "points": 0.5, "desc": "Contains unsubscription link."})

    # Ensure score is within 0 to 10 bounds
    final_score = max(0.0, min(10.0, score))
    
    return {
        "score": round(final_score, 1),
        "details": details
    }
