from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from .nlp_models import (
    ENGLISH_DATASET_PATH,
    LANGUAGE_DATA_FILES,
    LANGUAGE_MODEL_PATH,
    LANGUAGE_MODEL_V1_PATH,
    MODEL_FILES_DIR,
    SPAM_MODEL_PATH,
    SPAM_TFIDF_PATH,
    SPANISH_DATASET_PATH,
    SUPPORTED_LANGUAGES,
    atomic_joblib_dump,
    build_local_db_training_frame,
    clean_email_text,
    load_language_model,
)


def _print_metrics(name: str, y_true: Any, y_pred: Any) -> None:
    print(f"\n{name} accuracy: {accuracy_score(y_true, y_pred):.4f}")
    print(classification_report(y_true, y_pred))


def train_language_model(max_samples_per_language: int = 300000) -> Path:
    texts: list[str] = []
    labels: list[str] = []

    for language, path in LANGUAGE_DATA_FILES.items():
        print(f"Loading language samples for {language} from {path}...")
        count = 0
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if len(line) <= 30:
                    continue
                texts.append(line)
                labels.append(language)
                count += 1
                if count >= max_samples_per_language:
                    break

    df = pd.DataFrame({"text": texts, "language": labels})
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"],
        df["language"],
        test_size=0.2,
        random_state=42,
        stratify=df["language"],
    )

    model = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(analyzer="char", ngram_range=(3, 6), min_df=5),
            ),
            (
                "classifier",
                LogisticRegression(max_iter=1000, verbose=1),
            ),
        ]
    )

    start = time.perf_counter()
    model.fit(X_train, y_train)
    elapsed = time.perf_counter() - start
    print(f"Language model trained in {elapsed:.2f}s")

    predictions = model.predict(X_test)
    _print_metrics("Language model", y_test, predictions)

    atomic_joblib_dump(model, LANGUAGE_MODEL_PATH)
    atomic_joblib_dump(model, LANGUAGE_MODEL_V1_PATH)
    print(f"Saved language models to {LANGUAGE_MODEL_PATH} and {LANGUAGE_MODEL_V1_PATH}")
    return LANGUAGE_MODEL_PATH


def _read_spam_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required_columns = {"subject", "message", "label"}
    missing = required_columns - set(df.columns)
    if missing:
        raise ValueError(f"Dataset {path} is missing required columns: {sorted(missing)}")
    return df.copy()


def _prepare_base_spam_dataset() -> pd.DataFrame:
    english_df = _read_spam_dataset(ENGLISH_DATASET_PATH)
    spanish_df = _read_spam_dataset(SPANISH_DATASET_PATH)
    df = pd.concat([english_df, spanish_df], ignore_index=True)
    df["subject"] = df["subject"].fillna("")
    df["message"] = df["message"].fillna("")
    df["text"] = df["subject"] + " " + df["message"]
    df["clean_text"] = df["text"].apply(clean_email_text)
    df["label"] = df["label"].astype(str).str.upper().str.strip()
    df["source"] = df.get("language", "base_dataset")
    return df[df["clean_text"] != ""].copy()


def _attach_language_to_local_db(language_model: Any, local_df: pd.DataFrame) -> pd.DataFrame:
    if local_df.empty:
        local_df["language"] = []
        return local_df
    local_df = local_df.copy()
    local_df["language"] = local_df["clean_text"].apply(lambda value: str(language_model.predict([value])[0]))
    return local_df[local_df["language"].isin(SUPPORTED_LANGUAGES)].copy()


def train_spam_model(include_local_db: bool = False) -> tuple[Path, Path]:
    df = _prepare_base_spam_dataset()

    if include_local_db:
        print("Loading manually labeled emails from mailclient/maildatabase.json...")
        language_model = load_language_model()
        local_df = build_local_db_training_frame()
        local_df = _attach_language_to_local_db(language_model, local_df)
        if not local_df.empty:
            print(f"Including {len(local_df)} manually labeled database emails after language filtering.")
            df = pd.concat([df, local_df], ignore_index=True)
        else:
            print("No eligible manually labeled database emails were found.")

    df = df.drop_duplicates(subset=["clean_text", "label"]).reset_index(drop=True)

    X_train_text, X_test_text, y_train, y_test = train_test_split(
        df["clean_text"],
        df["label"],
        test_size=0.20,
        random_state=42,
        stratify=df["label"],
    )

    tfidf_spam = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        max_features=50000,
        min_df=2,
    )
    X_train = tfidf_spam.fit_transform(X_train_text)
    X_test = tfidf_spam.transform(X_test_text)

    spam_model = LinearSVC()
    start = time.perf_counter()
    spam_model.fit(X_train, y_train)
    elapsed = time.perf_counter() - start
    print(f"Spam model trained in {elapsed:.2f}s")

    predictions = spam_model.predict(X_test)
    _print_metrics("Spam model", y_test, predictions)

    atomic_joblib_dump(spam_model, SPAM_MODEL_PATH)
    atomic_joblib_dump(tfidf_spam, SPAM_TFIDF_PATH)
    print(f"Saved spam model to {SPAM_MODEL_PATH}")
    print(f"Saved spam vectorizer to {SPAM_TFIDF_PATH}")
    return SPAM_MODEL_PATH, SPAM_TFIDF_PATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train NinjaSpam NLP models from pure Python.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    language_parser = subparsers.add_parser("train-language", help="Train the language detector.")
    language_parser.add_argument("--max-samples-per-language", type=int, default=300000)

    spam_parser = subparsers.add_parser("train-spam", help="Train the spam/ham classifier.")
    spam_parser.add_argument("--include-local-db", action="store_true")

    all_parser = subparsers.add_parser("train-all", help="Train all models in the correct order.")
    all_parser.add_argument("--max-samples-per-language", type=int, default=300000)
    all_parser.add_argument("--include-local-db", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    MODEL_FILES_DIR.mkdir(parents=True, exist_ok=True)

    if args.command == "train-language":
        train_language_model(max_samples_per_language=args.max_samples_per_language)
        return 0
    if args.command == "train-spam":
        train_spam_model(include_local_db=args.include_local_db)
        return 0
    if args.command == "train-all":
        train_language_model(max_samples_per_language=args.max_samples_per_language)
        train_spam_model(include_local_db=args.include_local_db)
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
