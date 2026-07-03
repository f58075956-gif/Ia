"""Memoria persistente simple basada en un archivo JSON."""
import json
import os
from config import MEMORY_FILE


def _ensure_file():
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def load_memory() -> dict:
    _ensure_file()
    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_memory(data: dict):
    _ensure_file()
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def remember(key: str, value: str) -> str:
    data = load_memory()
    data[key] = value
    save_memory(data)
    return f"Guardado: {key} = {value}"


def recall(key: str) -> str:
    data = load_memory()
    if key in data:
        return str(data[key])
    return f"No tengo nada guardado bajo '{key}'."


def recall_all() -> str:
    data = load_memory()
    if not data:
        return "No hay nada en la memoria todavía."
    return json.dumps(data, ensure_ascii=False, indent=2)


def forget(key: str) -> str:
    data = load_memory()
    if key in data:
        del data[key]
        save_memory(data)
        return f"Olvidé '{key}'."
    return f"No tenía nada guardado bajo '{key}'."
