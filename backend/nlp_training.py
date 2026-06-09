from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from backend.nlp_models import (
        ENGLISH_DATASET_PATH,
        LANGUAGE_DATA_FILES,
        LANGUAGE_MODEL_PATH,
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
else:
    from .nlp_models import (
        ENGLISH_DATASET_PATH,
        LANGUAGE_DATA_FILES,
        LANGUAGE_MODEL_PATH,
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


def _print_confusion_matrix(name: str, y_true: Any, y_pred: Any, labels: list[str]) -> None:
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    matrix_df = pd.DataFrame(matrix, index=[f"true_{label}" for label in labels], columns=[f"pred_{label}" for label in labels])
    print(f"\n{name} confusion matrix:")
    print(matrix_df.to_string())


def _print_length_bucket_metrics(texts: pd.Series, y_true: pd.Series, y_pred: Any, name: str) -> None:
    bucketed = pd.DataFrame({"text": texts, "y_true": y_true, "y_pred": y_pred})
    bucketed["length"] = bucketed["text"].astype(str).str.len()

    def bucket_for_length(length: int) -> str:
        if length <= 20:
            return "short_0_20"
        if length <= 50:
            return "medium_21_50"
        return "long_51_plus"

    bucketed["bucket"] = bucketed["length"].apply(bucket_for_length)
    print(f"\n{name} accuracy by text-length bucket:")
    for bucket_name in ["short_0_20", "medium_21_50", "long_51_plus"]:
        subset = bucketed[bucketed["bucket"] == bucket_name]
        if subset.empty:
            print(f"- {bucket_name}: no samples")
            continue
        score = accuracy_score(subset["y_true"], subset["y_pred"])
        print(f"- {bucket_name}: accuracy={score:.4f} (n={len(subset)})")


def _progress(message: str) -> None:
    print(f"[language-training] {message}", flush=True)


def train_language_model(
    max_samples_per_language: int = 300000,
    min_text_length: int = 10,
    cv_folds: int = 3,
    n_jobs: int = 1,
) -> Path:
    texts: list[str] = []
    labels: list[str] = []

    _progress(
        f"Starting language training with max_samples_per_language={max_samples_per_language}, "
        f"min_text_length={min_text_length}"
    )

    for language, path in LANGUAGE_DATA_FILES.items():
        _progress(f"Loading language samples for {language} from {path}...")
        count = 0
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                line = line.strip()
                if len(line) < min_text_length:
                    continue
                texts.append(line)
                labels.append(language)
                count += 1
                if count % 50000 == 0:
                    _progress(f"{language}: accepted {count} samples so far")
                if count >= max_samples_per_language:
                    break
        _progress(f"Finished loading {language}: accepted {count} samples")

    df = pd.DataFrame({"text": texts, "language": labels})
    if df.empty:
        raise ValueError("No language samples were loaded. Check corpus files and minimum text length.")

    _progress(f"Total accepted language samples: {len(df)}")
    _progress(f"Per-language counts:\n{df['language'].value_counts().to_string()}")

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
                TfidfVectorizer(analyzer="char"),
            ),
            (
                "classifier",
                LogisticRegression(max_iter=1500),
            ),
        ]
    )

    param_grid = {
        "tfidf__ngram_range": [(2, 5), (3, 5), (3, 6)],
        "tfidf__min_df": [2, 3, 5],
        "classifier__C": [0.5, 1.0, 2.0],
    }

    total_candidates = (
        len(param_grid["tfidf__ngram_range"])
        * len(param_grid["tfidf__min_df"])
        * len(param_grid["classifier__C"])
    )
    _progress(
        f"Prepared grid search with {total_candidates} parameter combinations and {cv_folds}-fold CV "
        f"({total_candidates * cv_folds} total fits, n_jobs={n_jobs})"
    )

    search = GridSearchCV(
        estimator=model,
        param_grid=param_grid,
        cv=StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42),
        n_jobs=n_jobs,
        scoring="accuracy",
        verbose=3,
    )

    _progress("Starting GridSearchCV fit. You should now see periodic sklearn progress logs.")
    start = time.perf_counter()
    search.fit(X_train, y_train)
    elapsed = time.perf_counter() - start
    _progress(f"Language model selection/training completed in {elapsed:.2f}s")
    _progress(f"Best language params: {search.best_params_}")
    _progress(f"Best CV score: {search.best_score_:.4f}")

    best_model = search.best_estimator_
    _progress("Evaluating best language model on held-out test split...")
    predictions = best_model.predict(X_test)
    _print_metrics("Language model", y_test, predictions)
    _print_confusion_matrix("Language model", y_test, predictions, labels=sorted(df["language"].unique()))
    _print_length_bucket_metrics(X_test, y_test, predictions, "Language model")

    atomic_joblib_dump(best_model, LANGUAGE_MODEL_PATH)
    _progress(f"Saved language model to {LANGUAGE_MODEL_PATH}")
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
    language_parser.add_argument("--min-language-text-length", type=int, default=10)
    language_parser.add_argument("--cv-folds", type=int, default=3)
    language_parser.add_argument("--jobs", type=int, default=1)

    spam_parser = subparsers.add_parser("train-spam", help="Train the spam/ham classifier.")
    spam_parser.add_argument("--include-local-db", action="store_true")

    all_parser = subparsers.add_parser("train-all", help="Train all models in the correct order.")
    all_parser.add_argument("--max-samples-per-language", type=int, default=300000)
    all_parser.add_argument("--min-language-text-length", type=int, default=10)
    all_parser.add_argument("--cv-folds", type=int, default=3)
    all_parser.add_argument("--jobs", type=int, default=1)
    all_parser.add_argument("--include-local-db", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    MODEL_FILES_DIR.mkdir(parents=True, exist_ok=True)

    if args.command == "train-language":
        train_language_model(
            max_samples_per_language=args.max_samples_per_language,
            min_text_length=args.min_language_text_length,
            cv_folds=args.cv_folds,
            n_jobs=args.jobs,
        )
        return 0
    if args.command == "train-spam":
        train_spam_model(include_local_db=args.include_local_db)
        return 0
    if args.command == "train-all":
        train_language_model(
            max_samples_per_language=args.max_samples_per_language,
            min_text_length=args.min_language_text_length,
            cv_folds=args.cv_folds,
            n_jobs=args.jobs,
        )
        train_spam_model(include_local_db=args.include_local_db)
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
