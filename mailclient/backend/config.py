from __future__ import annotations

import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
SECRET_PATH = BASE_DIR / "secret.json"

DEFAULT_CONNECTION = {
    "host": "mail.ando.mx",
    "port": 993,
    "username": os.environ.get("IMAP_USER", "user@example.com"),
    "password": os.environ.get("IMAP_PASS", "password"),
    "ssl": True,
}


DEFAULT_PREFERENCES = {
    "allowed_languages": ["EN", "ES"],
    "allowed_countries": ["MX", "US", "ES"],
    "allow_links": True,
    "allow_undisclosed": False,
    "duplicate_subject_threshold": 3,
}


DEFAULT_CONFIG = {
    "connection": DEFAULT_CONNECTION,
    "preferences": DEFAULT_PREFERENCES,
}


def _deep_merge(base: dict, overrides: dict) -> dict:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)

    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        stored_config = json.load(config_file)

    merged_config = _deep_merge(DEFAULT_CONFIG, stored_config)
    secret_data = load_secret()
    merged_config.setdefault("connection", {})["password"] = secret_data.get("password", "")
    return merged_config


def save_config(config_data: dict) -> dict:
    merged_config = _deep_merge(DEFAULT_CONFIG, config_data)
    password = merged_config.get("connection", {}).pop("password", "")

    with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
        json.dump(merged_config, config_file, indent=2)

    save_secret({"password": password})
    merged_config.setdefault("connection", {})["password"] = password
    return merged_config


def load_secret() -> dict:
    if not SECRET_PATH.exists():
        return {"password": ""}

    with SECRET_PATH.open("r", encoding="utf-8") as secret_file:
        return json.load(secret_file)


def save_secret(secret_data: dict) -> dict:
    merged_secret = {"password": secret_data.get("password", "")}
    with SECRET_PATH.open("w", encoding="utf-8") as secret_file:
        json.dump(merged_secret, secret_file, indent=2)
    return merged_secret
