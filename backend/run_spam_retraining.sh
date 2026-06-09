#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="/home/labsinpecs/public_html/unir/ninjaspam"
DEFAULT_VENV_PYTHON="/home/labsinpecs/virtualenv/public_html/unir/ninjaspam/3.11/bin/python"
LOG_DIR="$PROJECT_DIR/logs"
TMP_DIR="$PROJECT_DIR/tmp"
LOCK_DIR="$TMP_DIR/nlp_spam_retraining.lock"
LOG_FILE="$LOG_DIR/nlp_spam_retraining.log"

PYTHON_BIN="${NLP_SERVICE_PYTHON:-$DEFAULT_VENV_PYTHON}"

usage() {
  cat <<USAGE
Usage: $(basename "$0")

Runs spam-model retraining for NinjaSpam using the base datasets plus manually
labeled emails from mailclient/maildatabase.json.

Environment overrides:
  NLP_SERVICE_PYTHON  Override Python executable (${DEFAULT_VENV_PYTHON})

Files:
  Lock dir: ${LOCK_DIR}
  Log file: ${LOG_FILE}
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python executable not found or not executable: $PYTHON_BIN" >&2
  exit 1
fi

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "Project directory not found: $PROJECT_DIR" >&2
  exit 1
fi

mkdir -p "$LOG_DIR" "$TMP_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[spam-retraining] Another retraining run is already in progress. Lock dir: $LOCK_DIR" >&2
  exit 1
fi

cleanup() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

cd "$PROJECT_DIR"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

{
  echo "[$(timestamp)] [spam-retraining] Starting spam retraining job"
  echo "[$(timestamp)] [spam-retraining] Project dir: $PROJECT_DIR"
  echo "[$(timestamp)] [spam-retraining] Python: $PYTHON_BIN"
  "$PYTHON_BIN" backend/nlp_training.py train-spam --include-local-db
  echo "[$(timestamp)] [spam-retraining] Spam retraining completed successfully"
} >> "$LOG_FILE" 2>&1