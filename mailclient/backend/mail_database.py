from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "maildatabase.json"


def ensure_database() -> None:
    if not DATABASE_PATH.exists():
        DATABASE_PATH.write_text("[]\n", encoding="utf-8")


def load_database() -> dict[str, dict]:
    ensure_database()
    with DATABASE_PATH.open("r", encoding="utf-8") as database_file:
        data = json.load(database_file)
        # Migración automática de lista antigua a dict
        if isinstance(data, list):
            new_db = {}
            for record in data:
                key = record.get("message_id") or compute_fallback_id(record)
                new_db[key] = record
            save_database(new_db)
            return new_db
        return data


def save_database(records: dict[str, dict]) -> None:
    with DATABASE_PATH.open("w", encoding="utf-8") as database_file:
        json.dump(records, database_file, indent=2)


def compute_record_hash(record: dict) -> str:
    serialized = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

def normalize_email_record(email: dict, label: str) -> dict:
    normalized = {
        "uid": email.get("uid"),
        "subject": (email.get("subject") or "").strip(),
        "from": sorted(email.get("from") or []),
        "to": sorted(email.get("to") or []),
        "cc": sorted(email.get("cc") or []),
        "date": email.get("date") or "",
        "message_id": (email.get("message_id") or "").strip(),
        "content_type": (email.get("content_type") or "").strip(),
        "body": {
            "plain": email.get("body", {}).get("plain", ""),
            "html": email.get("body", {}).get("html", ""),
            "preferred": email.get("body", {}).get("preferred", ""),
        },
        "headers": sorted(
            [
                {
                    "name": (header.get("name") or "").strip(),
                    "value": (header.get("value") or "").strip(),
                }
                for header in (email.get("headers") or [])
            ],
            key=lambda item: (item["name"].lower(), item["value"].lower()),
        ),
    }
    normalized["record_hash"] = compute_record_hash(normalized)
    normalized["label"] = label
    return normalized


def compute_fallback_id(email: dict) -> str:
    # Si no hay message-id, creamos un hash único con remitente, asunto y fecha
    subject = str(email.get("subject") or "").strip()
    sender = str(email.get("from") or "").strip()
    date = str(email.get("date") or "").strip()
    raw = f"{sender}|{subject}|{date}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def get_email_id(email: dict) -> str:
    msg_id = (email.get("message_id") or "").strip()
    return msg_id if msg_id else compute_fallback_id(email)

def get_all_scores() -> dict[str, dict]:
    db = load_database()
    scores = {}
    for key, record in db.items():
        scores[key] = {
            "tech_score": record.get("tech_score"),
            "ai_score": record.get("ai_score"),
            "mitl_tag": record.get("mitl_tag") or record.get("label")
        }
    return scores

def update_email_scores(email: dict, tech_score: float | None = None, ai_score: int | None = None, mitl_tag: str | None = None) -> dict:
    db = load_database()
    email_id = get_email_id(email)
    
    if email_id not in db:
        # Si no existe, creamos el registro base normalizado
        # Solo lo normalizamos si es un correo completo (con body y headers)
        if "body" in email and "headers" in email:
            record = normalize_email_record(email, "")
            del record["label"]
        else:
            # Es solo un stub de la lista, guardamos la info básica
            record = {
                "message_id": email.get("message_id", ""),
                "subject": email.get("subject", ""),
                "from": email.get("from", ""),
                "date": email.get("date", "")
            }
        db[email_id] = record

    record = db[email_id]
    
    if tech_score is not None:
        record["tech_score"] = tech_score
    if ai_score is not None:
        record["ai_score"] = ai_score
    if mitl_tag is not None:
        record["mitl_tag"] = mitl_tag
        record["label"] = mitl_tag  # Para retrocompatibilidad
        
    save_database(db)
    return record


def clear_database() -> dict:
    save_database({})
    return {"cleared": True, "database_count": 0}


def test_email_with_stub(email: dict) -> dict:
    label = random.choice(["SPAM", "HAM"])
    confidence = round(random.uniform(0.51, 0.99), 2)
    return {
        "uid": email.get("uid"),
        "predicted_label": label,
        "confidence": confidence,
        "model": "stub-random-v1",
    }
