"""Herramientas base que el asistente puede invocar."""
import os
import subprocess
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from memory import remember, recall, recall_all, forget
from activity_log import read_recent_activity
from tools.web import WEB_TOOLS
from config import DYNAMIC_TOOLS_DIR, TOOL_TIMEOUT


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error leyendo el archivo: {e}"


def write_file(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Archivo escrito correctamente en {path}"
    except Exception as e:
        return f"Error escribiendo el archivo: {e}"


def list_files(path: str = ".") -> str:
    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return f"Error listando archivos: {e}"


def run_python(code: str) -> str:
    """Ejecuta código Python en un subproceso aislado y devuelve la salida."""
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=TOOL_TIMEOUT
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        return output or "(sin salida)"
    except subprocess.TimeoutExpired:
        return f"Error: el código tardó demasiado y fue cancelado (timeout {TOOL_TIMEOUT}s)."
    except Exception as e:
        return f"Error ejecutando el código: {e}"


def run_shell(command: str) -> str:
    """Ejecuta un comando de terminal. SIEMPRE pasa por confirmación del usuario."""
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=TOOL_TIMEOUT
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]: {result.stderr}"
        return output or "(sin salida)"
    except subprocess.TimeoutExpired:
        return f"Error: el comando tardó demasiado y fue cancelado (timeout {TOOL_TIMEOUT}s)."
    except Exception as e:
        return f"Error ejecutando el comando: {e}"


def create_tool(name: str, python_code: str, description: str) -> str:
    """
    Permite al asistente crearse una nueva herramienta.
    python_code debe definir una función con el mismo nombre que 'name'.
    La herramienta queda disponible recién en el próximo mensaje (se recarga el loop).
    """
    safe_name = "".join(c for c in name if c.isalnum() or c == "_")
    if not safe_name:
        return "Error: el nombre de la herramienta quedó vacío después de sanitizarlo. Elegí otro nombre."
    if safe_name in BUILTIN_TOOLS:
        return (f"Error: '{safe_name}' ya es una herramienta incorporada y no se puede "
                f"sobreescribir. Elegí otro nombre para la herramienta nueva.")
    path = os.path.join(DYNAMIC_TOOLS_DIR, f"{safe_name}.py")
    header = f'"""{description}"""\n'
    try:
        os.makedirs(DYNAMIC_TOOLS_DIR, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(header + python_code)
        return (f"Herramienta '{safe_name}' creada en {path}. "
                f"Estará disponible a partir del próximo mensaje.")
    except Exception as e:
        return f"Error creando la herramienta: {e}"


def delete_file(path: str) -> str:
    try:
        os.remove(path)
        return f"Archivo {path} eliminado."
    except Exception as e:
        return f"Error eliminando el archivo: {e}"


# Registro de herramientas: nombre -> (función, descripción, parámetros JSON-schema)
BUILTIN_TOOLS = {
    "read_file": {
        "fn": read_file,
        "description": "Lee el contenido de un archivo de texto.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Ruta del archivo"}},
            "required": ["path"],
        },
    },
    "write_file": {
        "fn": write_file,
        "description": "Escribe (o sobreescribe) contenido en un archivo.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    "list_files": {
        "fn": list_files,
        "description": "Lista los archivos de una carpeta.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Carpeta (default '.')"}},
            "required": [],
        },
    },
    "run_python": {
        "fn": run_python,
        "description": "Ejecuta código Python y devuelve la salida. Pide confirmación.",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
    },
    "run_shell": {
        "fn": run_shell,
        "description": "Ejecuta un comando de terminal. Pide confirmación.",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    "create_tool": {
        "fn": create_tool,
        "description": (
            "Crea una nueva herramienta propia escribiendo código Python. "
            "Usalo cuando necesites una capacidad que no tenés todavía. Pide confirmación."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nombre de la función/herramienta"},
                "python_code": {"type": "string", "description": "Código Python completo de la función"},
                "description": {"type": "string", "description": "Qué hace la herramienta"},
            },
            "required": ["name", "python_code", "description"],
        },
    },
    "delete_file": {
        "fn": delete_file,
        "description": "Elimina un archivo. Pide confirmación.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    "remember": {
        "fn": remember,
        "description": "Guarda un dato en la memoria persistente (clave-valor) para recordarlo entre sesiones.",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}, "value": {"type": "string"}},
            "required": ["key", "value"],
        },
    },
    "recall": {
        "fn": recall,
        "description": "Recupera un dato guardado previamente en la memoria.",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
    "recall_all": {
        "fn": lambda: recall_all(),
        "description": "Muestra todo lo que hay guardado en la memoria.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "forget": {
        "fn": forget,
        "description": "Elimina un dato de la memoria.",
        "parameters": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    },
    "review_own_activity": {
        "fn": read_recent_activity,
        "description": (
            "Revisa tu propio historial reciente de mensajes y herramientas usadas. "
            "Usalo para detectar tareas que se repiten seguido o que fallaron, y así "
            "decidir si conviene crearte una herramienta nueva con create_tool para "
            "resolverlas mejor la próxima vez."
        ),
        "parameters": {
            "type": "object",
            "properties": {"n": {"type": "integer", "description": "Cantidad de eventos a revisar (default 40)"}},
            "required": [],
        },
    },
}

# Se suman las herramientas de internet al registro base
BUILTIN_TOOLS.update(WEB_TOOLS)
