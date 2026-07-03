"""
Carga las herramientas incorporadas + las que el asistente se fue creando
dinámicamente en la carpeta dynamic_tools/.
Cada archivo dynamic_tools/<nombre>.py debe definir una función <nombre>(...)
y opcionalmente TOOL_SCHEMA (dict JSON-schema de sus parámetros).
"""
import os
import importlib.util
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.builtin import BUILTIN_TOOLS
from config import DYNAMIC_TOOLS_DIR


def load_all_tools() -> dict:
    tools = dict(BUILTIN_TOOLS)

    if not os.path.isdir(DYNAMIC_TOOLS_DIR):
        return tools

    for filename in os.listdir(DYNAMIC_TOOLS_DIR):
        if not filename.endswith(".py"):
            continue
        name = filename[:-3]
        path = os.path.join(DYNAMIC_TOOLS_DIR, filename)
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            fn = getattr(module, name, None)
            if fn is None:
                continue
            schema = getattr(module, "TOOL_SCHEMA", {
                "type": "object", "properties": {}, "required": []
            })
            doc = (fn.__doc__ or f"Herramienta dinámica: {name}").strip()
            tools[name] = {"fn": fn, "description": doc, "parameters": schema}
        except Exception as e:
            print(f"[WARN] No se pudo cargar la herramienta dinámica '{name}': {e}")

    return tools


def to_ollama_schema(tools: dict) -> list:
    """Convierte el registro de herramientas al formato que espera Ollama."""
    schema = []
    for name, meta in tools.items():
        schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": meta["description"],
                "parameters": meta["parameters"],
            },
        })
    return schema
