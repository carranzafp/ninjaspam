#!/usr/bin/env bash
set -euo pipefail

HOST="127.0.0.1"
PORT="8765"
SUBJECT=""
BODY=""

usage() {
  cat <<'USAGE'
Usage: ./backend/test_prediction_service.sh --subject "Hello" --body "Message text" [--host 127.0.0.1] [--port 8765]

Sends a JSON request to the NinjaSpam TCP prediction service and prints the JSON response.

Options:
  --subject   Email subject to analyze
  --body      Email body to analyze
  --host      Service host (default: 127.0.0.1)
  --port      Service port (default: 8765)
  -h, --help  Show this help message

Example:
  ./backend/test_prediction_service.sh \
    --subject "Win a free prize" \
    --body "Click here now to claim your reward" \
    --host 127.0.0.1 \
    --port 8765
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --subject)
      SUBJECT="${2:-}"
      shift 2
      ;;
    --body)
      BODY="${2:-}"
      shift 2
      ;;
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$SUBJECT" && -z "$BODY" ]]; then
  echo "Error: at least one of --subject or --body must be provided." >&2
  usage >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required to run this client." >&2
  exit 1
fi

python3 - "$HOST" "$PORT" "$SUBJECT" "$BODY" <<'PY'
import json
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
subject = sys.argv[3]
body = sys.argv[4]

payload = {
    "action": "predict_email",
    "subject": subject,
    "message": body,
}

encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")

with socket.create_connection((host, port), timeout=10) as sock:
    sock.sendall(encoded)
    response = b""
    while not response.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk

if not response:
    raise SystemExit("No response received from prediction service.")

parsed = json.loads(response.decode("utf-8").strip())
print(json.dumps(parsed, ensure_ascii=False, indent=2))
PY
