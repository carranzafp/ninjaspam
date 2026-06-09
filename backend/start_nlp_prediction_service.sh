#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="/home/labsinpecs/public_html/unir/ninjaspam"
DEFAULT_VENV_PYTHON="/home/labsinpecs/virtualenv/public_html/unir/ninjaspam/3.11/bin/python"
DEFAULT_HOST="127.0.0.1"
DEFAULT_PORT="8765"
DEFAULT_LOG_LEVEL="INFO"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/tmp"
PID_FILE="$PID_DIR/nlp_prediction_service.pid"
LOG_FILE="$LOG_DIR/nlp_prediction_service.log"

PYTHON_BIN="${NLP_SERVICE_PYTHON:-$DEFAULT_VENV_PYTHON}"
HOST="${NLP_SERVICE_HOST:-$DEFAULT_HOST}"
PORT="${NLP_SERVICE_PORT:-$DEFAULT_PORT}"
LOG_LEVEL="${NLP_SERVICE_LOG_LEVEL:-$DEFAULT_LOG_LEVEL}"
COMMAND="start"

usage() {
  cat <<USAGE
Usage: $(basename "$0") [start|stop|restart|status] [--host HOST] [--port PORT] [--log-level LEVEL]

Manages the NinjaSpam NLP prediction TCP service on the remote server.

Environment overrides:
  NLP_SERVICE_PYTHON     Override Python executable (${DEFAULT_VENV_PYTHON})
  NLP_SERVICE_HOST       Override default host (${DEFAULT_HOST})
  NLP_SERVICE_PORT       Override default port (${DEFAULT_PORT})
  NLP_SERVICE_LOG_LEVEL  Override default log level (${DEFAULT_LOG_LEVEL})

Files:
  PID file: ${PID_FILE}
  Log file: ${LOG_FILE}
USAGE
}

ensure_environment() {
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Python executable not found or not executable: $PYTHON_BIN" >&2
    exit 1
  fi

  if [[ ! -d "$PROJECT_DIR" ]]; then
    echo "Project directory not found: $PROJECT_DIR" >&2
    exit 1
  fi

  mkdir -p "$LOG_DIR" "$PID_DIR"
  cd "$PROJECT_DIR"
}

is_running() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    rm -f "$PID_FILE"
  fi
  return 1
}

start_service() {
  ensure_environment

  if is_running; then
    echo "[nlp-service] Already running with PID $(cat "$PID_FILE")"
    return 0
  fi

  echo "[nlp-service] Starting prediction service from $PROJECT_DIR"
  echo "[nlp-service] Python=$PYTHON_BIN"
  echo "[nlp-service] Host=$HOST Port=$PORT LogLevel=$LOG_LEVEL"
  echo "[nlp-service] Log file: $LOG_FILE"

  nohup "$PYTHON_BIN" backend/nlp_prediction_service.py \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "$LOG_LEVEL" \
    >> "$LOG_FILE" 2>&1 &

  local pid=$!
  echo "$pid" > "$PID_FILE"
  sleep 1

  if kill -0 "$pid" 2>/dev/null; then
    echo "[nlp-service] Started with PID $pid"
    return 0
  fi

  echo "[nlp-service] Failed to start. Check $LOG_FILE" >&2
  rm -f "$PID_FILE"
  return 1
}

stop_service() {
  ensure_environment

  if ! is_running; then
    echo "[nlp-service] Service is not running"
    return 0
  fi

  local pid
  pid="$(cat "$PID_FILE")"
  echo "[nlp-service] Stopping service PID $pid"
  kill "$pid"

  for _ in {1..10}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PID_FILE"
      echo "[nlp-service] Service stopped"
      return 0
    fi
    sleep 1
  done

  echo "[nlp-service] PID $pid did not stop gracefully, forcing termination"
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "[nlp-service] Service stopped"
}

status_service() {
  ensure_environment

  if is_running; then
    echo "[nlp-service] Service is running with PID $(cat "$PID_FILE")"
  else
    echo "[nlp-service] Service is not running"
  fi
}

restart_service() {
  stop_service
  start_service
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    start|stop|restart|status)
      COMMAND="$1"
      shift
      ;;
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

case "$COMMAND" in
  start)
    start_service
    ;;
  stop)
    stop_service
    ;;
  restart)
    restart_service
    ;;
  status)
    status_service
    ;;
esac