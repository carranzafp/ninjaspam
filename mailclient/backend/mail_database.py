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


def load_database() -> list[dict]:
    ensure_database()
    with DATABASE_PATH.open("r", encoding="utf-8") as database_file:
        return json.load(database_file)


def save_database(records: list[dict]) -> None:
    with DATABASE_PATH.open("w", encoding="utf-8") as database_file:
        json.dump(records, database_file, indent=2)


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


def compute_record_hash(record: dict) -> str:
    canonical_payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def store_labeled_email(email: dict, label: str) -> dict:
    records = load_database()
    normalized_record = normalize_email_record(email, label)

    existing_record = next((record for record in records if record.get("record_hash") == normalized_record["record_hash"]), None)
    if existing_record:
        label_changed = existing_record.get("label") != label
        if label_changed:
            existing_record["label"] = label
            save_database(records)
        return {
            "stored": False,
            "duplicate": True,
            "updated": label_changed,
            "record": existing_record,
            "database_count": len(records),
        }

    records.append(normalized_record)
    save_database(records)
    return {
        "stored": True,
        "duplicate": False,
        "updated": False,
        "record": normalized_record,
        "database_count": len(records),
    }


def clear_database() -> dict:
    save_database([])
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
