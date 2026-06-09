from __future__ import annotations

# Proyecto NinjaSpam - Entrega 1
# Archivo principal de rutas y configuración del servidor Flask

import json
import os
import socket
from pathlib import Path

from flask import Flask, send_from_directory, request, jsonify, Response
from dotenv import load_dotenv

load_dotenv()

from backend.config import DEFAULT_CONFIG, load_config, save_config
from backend.imap_service import ImapMailboxClient
from backend.mail_database import clear_database, ensure_database, test_email_with_stub, get_all_scores, update_email_scores, get_email_id, load_database
from backend.email_analyzer import calculate_header_score
from backend.ai_service import analyze_spam_with_ai


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
NLP_SERVICE_HOST = os.environ.get("NLP_SERVICE_HOST", "127.0.0.1")
NLP_SERVICE_PORT = int(os.environ.get("NLP_SERVICE_PORT", "8765"))
NLP_SERVICE_TIMEOUT = float(os.environ.get("NLP_SERVICE_TIMEOUT", "5"))

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
ensure_database()

def check_auth(username, password):
    expected_user = os.environ.get('WEB_AUTH_USER', 'admin')
    expected_pass = os.environ.get('WEB_AUTH_PASS', 'secret')
    return username == expected_user and password == expected_pass

def authenticate():
    return Response(
        'Acceso denegado. Ingresa el usuario y contraseña correctos.', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

@app.before_request
def require_auth():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.post("/api/command")
def api_command():
    try:
        message = request.get_json()
    except Exception:
        return jsonify(_error_response("invalid_json", "Message must be valid JSON."))

    command = message.get("command")
    payload = message.get("payload", {})

    if command == "connect":
        return jsonify(handle_connect(payload))
    elif command == "get_email_detail":
        return jsonify(handle_get_email_detail(payload))
    elif command == "mark_mitl":
        return jsonify(handle_mark_mitl(payload))
    elif command == "test_email":
        return jsonify(handle_test_email(payload))
    elif command == "clear_database":
        return jsonify(handle_clear_database(payload))
    elif command == "get_config":
        return jsonify(_success_response("config_loaded", {"config": load_config()}))
    elif command == "save_config":
        return jsonify(handle_save_config(payload))
    elif command == "analyze_ai":
        return jsonify(handle_analyze_ai(payload))
    elif command == "predict_inbox_rows":
        return jsonify(handle_predict_inbox_rows(payload))
    else:
        return jsonify(_error_response("unknown_command", f"Unsupported command: {command}"))

@app.get("/<path:path>")
def static_files(path: str):
    return send_from_directory(FRONTEND_DIR, path)





def handle_connect(payload: dict) -> dict:
    stored_config = load_config()
    connection = {**stored_config.get("connection", {}), **payload.get("connection", {})}
    preferences = stored_config.get("preferences", DEFAULT_CONFIG["preferences"])

    try:
        mailbox_client = ImapMailboxClient(
            host=connection["host"],
            port=int(connection["port"]),
            username=connection["username"],
            password=connection["password"],
            ssl=bool(connection.get("ssl", True)),
        )
        emails = mailbox_client.fetch_inbox_emails(limit=1000)
        
        # Attach scores from the database
        scores_db = get_all_scores()
        for email in emails:
            eid = get_email_id(email)
            db_record = scores_db.get(eid, {})
            email["tech_score"] = db_record.get("tech_score")
            email["ai_score"] = db_record.get("ai_score")
            email["mitl_tag"] = db_record.get("mitl_tag")
            email["predicted_label"] = None
            email["predicted_language"] = None
            email["predicted_language_confidence"] = None
            email["prediction_basis"] = None
            email["prediction_attempted"] = False
            
    except Exception as exc:
        return _error_response("connect_failed", str(exc))

    updated_config = save_config({"connection": connection, "preferences": preferences})
    return _success_response(
        "connect_result",
        {
            "emails": emails,
            "config": updated_config,
        },
    )


def handle_save_config(payload: dict) -> dict:
    preferences = payload.get("preferences", {})
    updated_config = save_config({"preferences": preferences})
    return _success_response("config_saved", {"config": updated_config})


def handle_get_email_detail(payload: dict) -> dict:
    uid = payload.get("uid")
    if uid is None:
        return _error_response("email_detail", "Missing email UID.")

    stored_config = load_config()
    connection = stored_config.get("connection", {})

    try:
        mailbox_client = ImapMailboxClient(
            host=connection["host"],
            port=int(connection["port"]),
            username=connection["username"],
            password=connection["password"],
            ssl=bool(connection.get("ssl", True)),
        )
        email_detail = mailbox_client.fetch_email_detail(int(uid))
        header_score = calculate_header_score(email_detail.get("headers", []))
        email_detail["header_score"] = header_score

        prediction = _predict_email_record(email_detail)
        email_detail.update(prediction)
        
        # Save tech_score to the database automatically
        update_email_scores(email_detail, tech_score=header_score["score"])
        
    except Exception as exc:
        return _error_response("email_detail", str(exc))

    return _success_response("email_detail", {"email": email_detail})


def handle_mark_mitl(payload: dict) -> dict:
    label = (payload.get("label") or "").upper()
    if label not in {"SPAM", "HAM"}:
        return _error_response("mitl_marked", "Label must be SPAM or HAM.")

    email_detail = _fetch_email_detail_by_uid(payload.get("uid"))
    if isinstance(email_detail, dict) and email_detail.get("error"):
        return _error_response("mitl_marked", email_detail["error"])

    result = update_email_scores(email_detail, mitl_tag=label)
    return _success_response("mitl_marked", {"mitl_tag": label})


def handle_test_email(payload: dict) -> dict:
    email_detail = _fetch_email_detail_by_uid(payload.get("uid"))
    if isinstance(email_detail, dict) and email_detail.get("error"):
        return _error_response("email_tested", email_detail["error"])

    result = test_email_with_stub(email_detail)
    return _success_response("email_tested", result)


def handle_clear_database(payload: dict) -> dict:
    confirmation = payload.get("confirmation")
    if confirmation not in {"yes", "YES"}:
        return _error_response("database_cleared", 'Database clear requires confirmation set to "yes" or "YES".')

    return _success_response("database_cleared", clear_database())


def handle_analyze_ai(payload: dict) -> dict:
    email_detail = _fetch_email_detail_by_uid(payload.get("uid"))
    if isinstance(email_detail, dict) and email_detail.get("error"):
        return _error_response("ai_analyzed", email_detail["error"])

    result = analyze_spam_with_ai(email_detail)
    if not result.get("success"):
        return _error_response("ai_analyzed", result.get("error", "Unknown error"))
        
    # Save the AI score
    update_email_scores(email_detail, ai_score=result["spam_probability"])
        
    return _success_response("ai_analyzed", result)


def handle_predict_inbox_rows(payload: dict) -> dict:
    emails = payload.get("emails") or []
    if not isinstance(emails, list):
        return _error_response("inbox_predictions", "Payload field 'emails' must be a list.")

    scores_db = get_all_scores()
    full_db = load_database()
    predictions = []

    for email in emails:
        if not isinstance(email, dict):
            continue
        try:
            stub = {
                "uid": email.get("uid"),
                "message_id": email.get("message_id"),
                "subject": email.get("subject"),
                "from": email.get("from"),
                "date": email.get("date"),
            }
            prediction = _predict_email_record(stub, scores_db=scores_db, full_db=full_db)
            prediction["uid"] = email.get("uid")
            predictions.append(prediction)
        except Exception as exc:
            predictions.append(
                {
                    "uid": email.get("uid"),
                    "predicted_label": None,
                    "predicted_language": None,
                    "predicted_language_confidence": None,
                    "prediction_basis": None,
                    "prediction_attempted": True,
                    "prediction_error": str(exc),
                }
            )

    return _success_response("inbox_predictions", {"predictions": predictions})


def _fetch_email_detail_by_uid(uid: int | None) -> dict:
    if uid is None:
        return {"error": "Missing email UID."}

    stored_config = load_config()
    connection = stored_config.get("connection", {})

    try:
        mailbox_client = ImapMailboxClient(
            host=connection["host"],
            port=int(connection["port"]),
            username=connection["username"],
            password=connection["password"],
            ssl=bool(connection.get("ssl", True)),
        )
        return mailbox_client.fetch_email_detail(int(uid))
    except Exception as exc:
        return {"error": str(exc)}


def _send_nlp_request(payload: dict) -> dict:
    encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    with socket.create_connection((NLP_SERVICE_HOST, NLP_SERVICE_PORT), timeout=NLP_SERVICE_TIMEOUT) as sock:
        sock.sendall(encoded)
        response_bytes = b""
        while not response_bytes.endswith(b"\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_bytes += chunk

    if not response_bytes:
        raise RuntimeError("NLP service returned an empty response.")

    response = json.loads(response_bytes.decode("utf-8").strip())
    if not response.get("ok"):
        raise RuntimeError(str(response.get("error") or "Unknown NLP service error."))
    return response


def _body_from_db_record(record: dict | None) -> str:
    if not record:
        return ""
    body = record.get("body") or {}
    if isinstance(body, dict):
        return str(body.get("preferred") or body.get("plain") or body.get("html") or "")
    return str(body or "")


def _predict_email_record(email: dict, scores_db: dict | None = None, full_db: dict | None = None) -> dict:
    scores_db = scores_db or get_all_scores()
    full_db = full_db or load_database()
    email_id = get_email_id(email)
    db_record = scores_db.get(email_id) or {}
    full_record = full_db.get(email_id) or {}

    subject = str(email.get("subject") or "")
    body = ""
    prediction_basis = "subject_only"

    email_body = email.get("body") or {}
    if isinstance(email_body, dict):
        body = str(email_body.get("preferred") or email_body.get("plain") or email_body.get("html") or "")
    elif email_body:
        body = str(email_body)

    if not body:
        body = _body_from_db_record(full_record) or _body_from_db_record(db_record)

    if body:
        prediction_basis = "subject_and_body"

    prediction = _send_nlp_request({"action": "predict_email", "subject": subject, "message": body})

    return {
        "predicted_label": prediction.get("spam_label"),
        "predicted_language": prediction.get("language"),
        "predicted_language_confidence": prediction.get("language_confidence"),
        "prediction_basis": prediction_basis,
        "prediction_attempted": True,
    }


def _success_response(event: str, payload: dict) -> dict:
    return {"event": event, "success": True, **payload}


def _error_response(event: str, message: str) -> dict:
    return {"event": event, "success": False, "error": message}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
