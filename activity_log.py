"""
Log de todo lo que hace el asistente (mensajes, herramientas usadas, resultados).
Sirve como base para que el asistente pueda mirar hacia atrás, notar tareas
repetidas o fallidas, y decidir crearse una herramienta nueva para mejorar.
"""
import json
import os
import time

from config import LOG_FILE


def log_event(kind: str, detail: dict):
    """kind: 'user_message' | 'tool_call' | 'tool_result' | 'assistant_message'"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    entry = {"ts": time.time(), "kind": kind, **detail}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_recent_activity(n: int = 40) -> str:
    """Devuelve las últimas n entradas del log, en formato legible."""
    if not os.path.exists(LOG_FILE):
        return "Todavía no hay actividad registrada."
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()[-n:]
    out = []
    for line in lines:
        try:
            e = json.loads(line)
            out.append(f"[{e['kind']}] {json.dumps({k:v for k,v in e.items() if k not in ('ts','kind')}, ensure_ascii=False)}")
        except Exception:
            continue
    return "\n".join(out) if out else "Todavía no hay actividad registrada."
