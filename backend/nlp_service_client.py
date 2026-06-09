from __future__ import annotations

import json
import socket
from typing import Any


class NlpServiceError(RuntimeError):
    """Raised when the NLP socket service fails or returns an error."""


def send_request(payload: dict[str, Any], host: str = "127.0.0.1", port: int = 8765, timeout: float = 10.0) -> dict[str, Any]:
    encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(encoded)
            response_bytes = b""
            while not response_bytes.endswith(b"\n"):
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_bytes += chunk
    except OSError as exc:
        raise NlpServiceError(f"Could not connect to NLP service at {host}:{port}: {exc}") from exc

    if not response_bytes:
        raise NlpServiceError("NLP service returned an empty response.")

    try:
        response = json.loads(response_bytes.decode("utf-8").strip())
    except json.JSONDecodeError as exc:
        raise NlpServiceError("NLP service returned invalid JSON.") from exc

    if not response.get("ok"):
        raise NlpServiceError(str(response.get("error") or "Unknown NLP service error."))
    return response


def health(host: str = "127.0.0.1", port: int = 8765, timeout: float = 5.0) -> dict[str, Any]:
    return send_request({"action": "health"}, host=host, port=port, timeout=timeout)


def predict_email(subject: str, message: str, host: str = "127.0.0.1", port: int = 8765, timeout: float = 10.0) -> dict[str, Any]:
    return send_request(
        {"action": "predict_email", "subject": subject, "message": message},
        host=host,
        port=port,
        timeout=timeout,
    )


def predict_text(text: str, host: str = "127.0.0.1", port: int = 8765, timeout: float = 10.0) -> dict[str, Any]:
    return send_request({"action": "predict_text", "text": text}, host=host, port=port, timeout=timeout)
