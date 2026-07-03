"""
Persistencia de conversaciones en disco (data/conversations/<id>.json), para
no perder el historial cada vez que se reinicia main.py o webapp/server.py.

Conversation persistence to disk (data/conversations/<id>.json), so the chat
history survives restarts of main.py or webapp/server.py.
"""
import json
import os

from config import CONVERSATIONS_DIR


def _path(session_id: str) -> str:
    safe_id = "".join(c for c in session_id if c.isalnum() or c in ("-", "_")) or "default"
    return os.path.join(CONVERSATIONS_DIR, f"{safe_id}.json")


def _to_plain(msg):
    """
    Convierte un mensaje a dict plano serializable. Los mensajes que agregamos
    nosotros ya son dicts, pero los que devuelve la librería 'ollama' pueden
    ser objetos tipo pydantic (con .model_dump()) según la versión instalada.
    """
    if isinstance(msg, dict):
        return msg
    if hasattr(msg, "model_dump"):
        return msg.model_dump()
    try:
        return dict(msg)
    except Exception:
        return {"role": getattr(msg, "role", "assistant"), "content": str(getattr(msg, "content", msg))}


def save_conversation(session_id: str, messages: list):
    """Guarda la conversación completa. Escritura atómica para no corromper
    el archivo si el proceso se corta a mitad de la escritura (común en
    Termux, donde Android puede matar el proceso en cualquier momento)."""
    os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
    path = _path(session_id)
    tmp_path = path + ".tmp"
    try:
        plain = [_to_plain(m) for m in messages]
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(plain, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        print(f"[WARN] No se pudo guardar la conversación / Could not save conversation: {e}")


def load_conversation(session_id: str):
    """Devuelve la lista de mensajes guardada, o None si no hay nada / no se pudo leer."""
    path = _path(session_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            return data
        return None
    except Exception as e:
        print(f"[WARN] No se pudo cargar la conversación guardada / Could not load saved conversation: {e}")
        return None


def reset_conversation(session_id: str):
    path = _path(session_id)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
