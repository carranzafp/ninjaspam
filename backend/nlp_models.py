from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent.parent
MODEL_FILES_DIR = ROOT_DIR / "model_files"
MAILCLIENT_DIR = ROOT_DIR / "mailclient"
MAIL_DATABASE_PATH = MAILCLIENT_DIR / "maildatabase.json"

LANGUAGE_DATA_FILES = {
    "spanish": MODEL_FILES_DIR / "es.txt",
    "english": MODEL_FILES_DIR / "en.txt",
    "french": MODEL_FILES_DIR / "fr.txt",
}

# Portuguese is intentionally excluded from the default training set because
# the current `pt.txt` corpus is disproportionately large for the repository.
# If needed later, it can be re-enabled with a curated or trimmed sample file.
OPTIONAL_LANGUAGE_DATA_FILES = {
    "portuguese": MODEL_FILES_DIR / "pt.txt",
}

ENGLISH_DATASET_PATH = MODEL_FILES_DIR / "english_dataset.csv"
SPANISH_DATASET_PATH = MODEL_FILES_DIR / "spanish_dataset.csv"

LANGUAGE_MODEL_PATH = MODEL_FILES_DIR / "language_detector.pkl"
LANGUAGE_MODEL_V1_PATH = MODEL_FILES_DIR / "language_detector_v1.pkl"
SPAM_MODEL_PATH = MODEL_FILES_DIR / "spam_ham_model.pkl"
SPAM_TFIDF_PATH = MODEL_FILES_DIR / "tfidf_spam.pkl"

SUPPORTED_LANGUAGES = tuple(LANGUAGE_DATA_FILES.keys())
SUPPORTED_SPAM_LABELS = {"SPAM", "HAM"}


@dataclass(slots=True)
class InferenceBundle:
    language_model: Any
    spam_model: Any
    spam_vectorizer: Any


def atomic_joblib_dump(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name, suffix=".tmp", delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
    try:
        joblib.dump(obj, tmp_path)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def clean_email_text(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"http\S+|www\S+", " URL ", text)
    text = re.sub(r"\S+@\S+", " EMAIL ", text)
    text = re.sub(r"\d+", " NUMBER ", text)
    text = re.sub(r"[^a-záéíóúñüàèìòùâêîôûãõç\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def combine_subject_and_body(subject: str, body: str) -> str:
    return f"{(subject or '').strip()} {(body or '').strip()}".strip()


def extract_preferred_body(record: dict[str, Any]) -> str:
    body = record.get("body") or {}
    if isinstance(body, dict):
        return str(body.get("preferred") or body.get("plain") or body.get("html") or "")
    return str(body or "")


def load_mail_database_records(mail_database_path: Path = MAIL_DATABASE_PATH) -> list[dict[str, Any]]:
    if not mail_database_path.exists():
        return []
    with mail_database_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        return list(payload.values())
    if isinstance(payload, list):
        return payload
    return []


def build_local_db_training_frame(mail_database_path: Path = MAIL_DATABASE_PATH) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in load_mail_database_records(mail_database_path):
        label = str(record.get("label") or record.get("mitl_tag") or "").upper().strip()
        subject = str(record.get("subject") or "").strip()
        body = extract_preferred_body(record).strip()
        if label not in SUPPORTED_SPAM_LABELS:
            continue
        if not subject or not body:
            continue
        text = combine_subject_and_body(subject, body)
        clean_text = clean_email_text(text)
        if not clean_text:
            continue
        rows.append(
            {
                "subject": subject,
                "message": body,
                "text": text,
                "clean_text": clean_text,
                "label": label,
                "source": "maildatabase_manual",
                "message_id": record.get("message_id") or "",
            }
        )
    return pd.DataFrame(rows)


def load_language_model(path: Path | None = None) -> Any:
    preferred_path = path or LANGUAGE_MODEL_PATH
    if preferred_path.exists():
        return joblib.load(preferred_path)
    if LANGUAGE_MODEL_V1_PATH.exists():
        return joblib.load(LANGUAGE_MODEL_V1_PATH)
    raise FileNotFoundError("Language model PKL not found. Train the language model first.")


def load_spam_components(
    spam_model_path: Path = SPAM_MODEL_PATH,
    vectorizer_path: Path = SPAM_TFIDF_PATH,
) -> tuple[Any, Any]:
    if not spam_model_path.exists():
        raise FileNotFoundError(f"Spam model PKL not found: {spam_model_path}")
    if not vectorizer_path.exists():
        raise FileNotFoundError(f"Spam TF-IDF PKL not found: {vectorizer_path}")
    return joblib.load(spam_model_path), joblib.load(vectorizer_path)


def load_inference_bundle() -> InferenceBundle:
    spam_model, spam_vectorizer = load_spam_components()
    language_model = load_language_model()
    return InferenceBundle(
        language_model=language_model,
        spam_model=spam_model,
        spam_vectorizer=spam_vectorizer,
    )


def predict_language(text: str, language_model: Any) -> str:
    clean_text = clean_email_text(text)
    if not clean_text:
        return "unknown"
    return str(language_model.predict([clean_text])[0])


def predict_spam_label(text: str, spam_model: Any, spam_vectorizer: Any) -> str:
    clean_text = clean_email_text(text)
    vector = spam_vectorizer.transform([clean_text])
    return str(spam_model.predict(vector)[0])


def predict_email(subject: str, body: str, bundle: InferenceBundle) -> dict[str, Any]:
    combined = combine_subject_and_body(subject, body)
    clean_text = clean_email_text(combined)
    language = predict_language(combined, bundle.language_model) if clean_text else "unknown"
    spam_label = predict_spam_label(combined, bundle.spam_model, bundle.spam_vectorizer) if clean_text else "unknown"
    return {
        "language": language,
        "spam_label": spam_label,
        "clean_text": clean_text,
        "text": combined,
    }
