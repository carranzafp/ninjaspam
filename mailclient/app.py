from __future__ import annotations

import json
import os
from pathlib import Path

from flask import Flask, send_from_directory, request, jsonify, Response
from dotenv import load_dotenv

load_dotenv()

from backend.config import DEFAULT_CONFIG, load_config, save_config
from backend.imap_service import ImapMailboxClient
from backend.mail_database import clear_database, ensure_database, store_labeled_email, test_email_with_stub
from backend.email_analyzer import calculate_header_score
from backend.ai_service import analyze_spam_with_ai


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

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
    elif command == "classify_email":
        return jsonify(handle_classify_email(payload))
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
        emails = mailbox_client.fetch_inbox_emails()
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
    except Exception as exc:
        return _error_response("email_detail", str(exc))

    return _success_response("email_detail", {"email": email_detail})


def handle_classify_email(payload: dict) -> dict:
    label = (payload.get("label") or "").upper()
    if label not in {"SPAM", "HAM"}:
        return _error_response("email_classified", "Label must be SPAM or HAM.")

    email_detail = _fetch_email_detail_by_uid(payload.get("uid"))
    if isinstance(email_detail, dict) and email_detail.get("error"):
        return _error_response("email_classified", email_detail["error"])

    result = store_labeled_email(email_detail, label)
    return _success_response("email_classified", result)


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
    return _success_response("ai_analyzed", result)


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


def _success_response(event: str, payload: dict) -> dict:
    return {"event": event, "success": True, **payload}


def _error_response(event: str, message: str) -> dict:
    return {"event": event, "success": False, "error": message}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
