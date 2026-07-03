"""
Configuración central del asistente.
Cambiá MODEL por el nombre exacto del modelo que descargaste en Ollama, o
seteá la variable de entorno ASSISTANT_MODEL sin tocar este archivo.
Modelos recomendados que soportan "tool calling" (uso de herramientas):
  - "llama3.1"        (8B, buen balance velocidad/calidad — desktop/GPU)
  - "qwen2.5"          (7B/14B, muy bueno siguiendo instrucciones)
  - "mistral-nemo"     (12B)
  - "llama3.2:3b"      (liviano, recomendado para celular/Termux)
  - "llama3.2:1b"      (el más liviano, para equipos con poca RAM)
"""
import os

# Todas las rutas del proyecto se calculan relativas a este archivo, no al
# directorio desde el que se ejecuta python. Esto evita errores de "No such
# file or directory" en Termux, donde es común correr el script desde el
# home (~) en vez de la carpeta del proyecto.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Detección simple de Termux: la variable PREFIX apunta a
# /data/data/com.termux/files/usr cuando corremos dentro de Termux.
IS_TERMUX = "com.termux" in os.environ.get("PREFIX", "")

# En celular conviene un modelo bastante más chico por defecto (menos RAM/VRAM
# y CPU). Se puede pisar en cualquier entorno con la variable ASSISTANT_MODEL.
_DEFAULT_MODEL = "llama3.2:3b" if IS_TERMUX else "llama3.1"
MODEL = os.environ.get("ASSISTANT_MODEL", _DEFAULT_MODEL)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

MEMORY_FILE = os.path.join(BASE_DIR, "data", "memory.json")
DYNAMIC_TOOLS_DIR = os.path.join(BASE_DIR, "dynamic_tools")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloads")
LOG_FILE = os.path.join(BASE_DIR, "data", "activity_log.jsonl")
CONVERSATIONS_DIR = os.path.join(BASE_DIR, "data", "conversations")

# Timeout para run_python / run_shell. Un celular puede tardar bastante más
# que una compu de escritorio en tareas de CPU, así que en Termux se le da
# más margen por defecto. Se puede ajustar con ASSISTANT_TOOL_TIMEOUT.
TOOL_TIMEOUT = int(os.environ.get("ASSISTANT_TOOL_TIMEOUT", "45" if IS_TERMUX else "30"))

# Corte de seguridad: máximo de vueltas de tool-calling encadenadas por mensaje
# del usuario, para evitar que el asistente quede en un loop infinito pidiendo
# herramientas sin nunca responder.
MAX_TOOL_ITERATIONS = int(os.environ.get("ASSISTANT_MAX_TOOL_ITERATIONS", "10000"))

# Acciones que SIEMPRE piden confirmación por más autónomo que sea el asistente
DANGEROUS_ACTIONS = {"run_shell", "run_python", "create_tool", "delete_file", "download_file"}

SYSTEM_PROMPT = """Sos un asistente personal que corre localmente en la compu del usuario.
Tenés acceso a internet (buscar, leer páginas, descargar archivos), a leer/escribir
archivos, ejecutar código, recordar información entre conversaciones, revisar tu
propio historial de actividad, y crear nuevas herramientas para vos mismo cuando
detectás que necesitás una capacidad que no tenés todavía.

Reglas:
- Sé directo y útil, sin vueltas innecesarias.
- Idioma / Language: respondé siempre en el mismo idioma en el que te escribe
  el usuario — español o inglés — sin que haga falta pedirlo. Si un mensaje
  mezcla los dos, respondé en el que predomine. Podés cambiar de idioma de un
  mensaje a otro si el usuario cambia. / Always reply in whatever language the
  user just wrote in — Spanish or English — without being asked. If a message
  mixes both, reply in whichever dominates. You can switch languages message
  to message if the user does.
- Cuando la pregunta dependa de información actual, específica, o que no
  estés 100% seguro de recordar bien (fechas, cifras, nombres, hechos
  recientes, afirmaciones verificables), usá SIEMPRE web_search y web_fetch
  ANTES de responder, en vez de contestar de memoria. Priorizá fuentes
  primarias y confiables. Si buscaste y las fuentes no coinciden entre sí o
  no encontraste nada confiable, decilo explícitamente en vez de inventar
  una respuesta — nunca presentes una suposición como si fuera un hecho
  verificado. / When a question depends on current or specific information,
  or on anything you're not 100% sure you recall correctly (dates, figures,
  names, recent facts, verifiable claims), ALWAYS use web_search and
  web_fetch BEFORE answering, instead of answering from memory. Prefer
  primary, reliable sources. If sources disagree or you found nothing
  reliable, say so explicitly instead of guessing — never present an
  assumption as a verified fact.
- Si necesitás una herramienta que no existe, creála con create_tool. Es más valioso
  crearte una herramienta reutilizable que resolver algo "a mano" una sola vez.
- De vez en cuando, si notás que estás repitiendo el mismo tipo de tarea, usá
  review_own_activity para mirar tu historial reciente y evaluar si conviene
  automatizar algo con una herramienta nueva.
- Nunca ejecutes acciones destructivas o irreversibles sin que el usuario lo haya
  pedido explícitamente.
- Si no estás seguro de qué quiere el usuario, preguntá antes de actuar.
"""

if IS_TERMUX:
    SYSTEM_PROMPT += (
        "\nEstás corriendo en un celular Android (Termux), con menos RAM y CPU "
        "que una compu de escritorio. Preferí respuestas concisas y evitá tareas "
        "con run_python/run_shell que consuman mucha memoria o tarden mucho. / "
        "You're running on an Android phone (Termux), with less RAM and CPU than "
        "a desktop. Prefer concise answers and avoid run_python/run_shell tasks "
        "that use a lot of memory or take a long time.\n"
    )
