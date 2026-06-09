from __future__ import annotations

import argparse
import json
import logging
import socketserver
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from backend.nlp_models import InferenceBundle, load_inference_bundle, predict_email
else:
    from .nlp_models import InferenceBundle, load_inference_bundle, predict_email


LOGGER = logging.getLogger("backend.nlp_prediction_service")


class PredictionTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], handler_class: type[socketserver.BaseRequestHandler], bundle: InferenceBundle):
        self.bundle = bundle
        super().__init__(server_address, handler_class)


class PredictionRequestHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        raw_line = self.rfile.readline()
        if not raw_line:
            return

        try:
            request = json.loads(raw_line.decode("utf-8"))
            response = self.dispatch(request)
        except json.JSONDecodeError:
            response = {"ok": False, "error": "Invalid JSON request."}
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            LOGGER.exception("Unhandled prediction service error")
            response = {"ok": False, "error": str(exc)}

        self.wfile.write((json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8"))

    def dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        action = str(request.get("action") or "").strip().lower()
        if action == "health":
            return {"ok": True, "status": "healthy"}
        if action == "predict_email":
            subject = str(request.get("subject") or "")
            body = str(request.get("message") or request.get("body") or "")
            result = predict_email(subject, body, self.server.bundle)
            return {"ok": True, **result}
        if action == "predict_text":
            text = str(request.get("text") or "")
            result = predict_email("", text, self.server.bundle)
            return {"ok": True, **result}
        return {"ok": False, "error": f"Unsupported action: {action}"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the NinjaSpam TCP JSON prediction service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    bundle = load_inference_bundle()
    with PredictionTCPServer((args.host, args.port), PredictionRequestHandler, bundle=bundle) as server:
        LOGGER.info("Prediction service listening on %s:%s", args.host, args.port)
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
