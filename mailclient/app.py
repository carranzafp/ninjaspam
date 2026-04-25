from __future__ import annotations

import json
from pathlib import Path

from flask import Flask, send_from_directory
from flask_sock import Sock

from backend.config import DEFAULT_CONFIG, load_config, save_config
from backend.imap_service import ImapMailboxClient
from backend.mail_database import clear_database, ensure_database, store_labeled_email, test_email_with_stub


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
sock = Sock(app)
ensure_database()


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path: str):
    return send_from_directory(FRONTEND_DIR, path)


@sock.route("/ws")
def websocket_endpoint(ws):
    while True:
        raw_message = ws.receive()
        if raw_message is None:
            break

        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError:
            ws.send(json.dumps(_error_response("invalid_json", "Message must be valid JSON.")))
            continue

        command = message.get("command")
        payload = message.get("payload", {})

        if command == "connect":
            ws.send(json.dumps(handle_connect(payload)))
        elif command == "get_email_detail":
            ws.send(json.dumps(handle_get_email_detail(payload)))
        elif command == "classify_email":
            ws.send(json.dumps(handle_classify_email(payload)))
        elif command == "test_email":
            ws.send(json.dumps(handle_test_email(payload)))
        elif command == "clear_database":
            ws.send(json.dumps(handle_clear_database(payload)))
        elif command == "get_config":
            ws.send(json.dumps(_success_response("config_loaded", {"config": load_config()})))
        elif command == "save_config":
            ws.send(json.dumps(handle_save_config(payload)))
        else:
            ws.send(json.dumps(_error_response("unknown_command", f"Unsupported command: {command}")))


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
