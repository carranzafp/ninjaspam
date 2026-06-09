#!/usr/bin/env bash

set -euo pipefail

VENV_ACTIVATE="/home/labsinpecs/virtualenv/public_html/unir/ninjaspam/3.11/bin/activate"
PROJECT_DIR="/home/labsinpecs/public_html/unir/ninjaspam"
DEFAULT_HOST="127.0.0.1"
DEFAULT_PORT="8765"
DEFAULT_LOG_LEVEL="INFO"

HOST="${NLP_SERVICE_HOST:-$DEFAULT_HOST}"
PORT="${NLP_SERVICE_PORT:-$DEFAULT_PORT}"
LOG_LEVEL="${NLP_SERVICE_LOG_LEVEL:-$DEFAULT_LOG_LEVEL}"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--host HOST] [--port PORT] [--log-level LEVEL]

Starts the NinjaSpam NLP prediction TCP service on the remote server.

Environment overrides:
  NLP_SERVICE_HOST       Override default host (${DEFAULT_HOST})
  NLP_SERVICE_PORT       Override default port (${DEFAULT_PORT})
  NLP_SERVICE_LOG_LEVEL  Override default log level (${DEFAULT_LOG_LEVEL})
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --log-level)
      LOG_LEVEL="$2"
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

if [[ ! -f "$VENV_ACTIVATE" ]]; then
  echo "Virtualenv activation script not found: $VENV_ACTIVATE" >&2
  exit 1
fi

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Project directory not found: $PROJECT_DIR" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "$VENV_ACTIVATE"
cd "$PROJECT_DIR"

echo "[nlp-service] Starting prediction service from $PROJECT_DIR"
echo "[nlp-service] Host=$HOST Port=$PORT LogLevel=$LOG_LEVEL"

exec python backend/nlp_prediction_service.py \
  --host "$HOST" \
  --port "$PORT" \
  --log-level "$LOG_LEVEL"