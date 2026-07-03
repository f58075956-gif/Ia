"""
Backend web del asistente. Sirve la interfaz de chat y hace de puente entre
el navegador y Ollama + las herramientas (que no pueden correr en el browser).

Correr con: python webapp/server.py
Abrir en:   http://localhost:5000
"""
import json
import os
import secrets
import sys
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, send_from_directory, session

try:
    import ollama
except ImportError:
    print("Falta instalar 'ollama'. Corré: pip install ollama")
    sys.exit(1)

from config import MODEL, SYSTEM_PROMPT, DANGEROUS_ACTIONS, OLLAMA_HOST, IS_TERMUX, MAX_TOOL_ITERATIONS
from tools.loader import load_all_tools, to_ollama_schema
from activity_log import log_event
import conversation_store as convstore

# Cliente explícito apuntando a OLLAMA_HOST (respeta la variable de entorno
# del mismo nombre si se seteó, o localhost:11434 por defecto).
client = ollama.Client(host=OLLAMA_HOST)

app = Flask(__name__, static_folder="static", static_url_path="")
# Necesario para las cookies de sesión (una por pestaña/usuario). Si no se
# fija ASSISTANT_SECRET_KEY, se genera una al arrancar (las sesiones se
# invalidan al reiniciar el server, que es el comportamiento esperado para
# uso 100% local).
app.secret_key = os.environ.get("ASSISTANT_SECRET_KEY", secrets.token_hex(32))

# Bug arreglado: antes había un único STATE global compartido por todos los
# clientes, así que dos pestañas o dos personas usando la webapp al mismo
# tiempo se pisaban la conversación entre sí. Ahora cada sesión de navegador
# (cookie) tiene su propio estado, guardado en SESSIONS por session id.
# Además, cada conversación se persiste en disco (conversation_store), así
# que sobrevive a un reinicio del server (siempre que el navegador conserve
# la cookie de sesión).
SESSIONS = {}  # session_id -> {"messages": [...], "pending": {...}}


def get_state() -> dict:
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    sid = session["sid"]
    if sid not in SESSIONS:
        loaded = convstore.load_conversation(sid)
        if loaded:
            # El primer mensaje (system prompt) se pisa siempre con el
            # SYSTEM_PROMPT actual, para que los cambios en config.py se
            # apliquen aunque haya una conversación vieja guardada.
            loaded[0] = {"role": "system", "content": SYSTEM_PROMPT}
            SESSIONS[sid] = {"messages": loaded, "pending": {}}
        else:
            SESSIONS[sid] = {
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
                "pending": {},
            }
    return SESSIONS[sid]


def persist_state(state: dict):
    convstore.save_conversation(session["sid"], state["messages"])


def run_tool_now(tools, name, args):
    try:
        result = str(tools[name]["fn"](**args))
    except Exception as e:
        result = f"Error ejecutando '{name}': {e}"
    log_event("tool_call", {"name": name, "args": args, "result": result[:300]})
    return result


def step_conversation(state: dict):
    """
    Llama al modelo con el historial actual. Si el modelo pide una herramienta
    peligrosa, frena y devuelve un pedido de confirmación al frontend.
    Si pide una herramienta segura, la ejecuta automáticamente y sigue.
    """
    tools = load_all_tools()
    ollama_tools = to_ollama_schema(tools)

    iterations = 0
    while True:
        iterations += 1
        if iterations > MAX_TOOL_ITERATIONS:
            return {
                "type": "message",
                "content": (
                    f"⚠️ Reached the limit of {MAX_TOOL_ITERATIONS} chained tool calls "
                    f"for this message, stopping to avoid a loop. / "
                    f"Se alcanzó el límite de {MAX_TOOL_ITERATIONS} llamadas encadenadas, "
                    f"corto para evitar un loop."
                ),
            }
        try:
            response = client.chat(model=MODEL, messages=state["messages"], tools=ollama_tools)
        except Exception as e:
            state["messages"].pop()  # saca el mensaje que no se pudo procesar
            persist_state(state)
            hint = " ¿Corriste 'ollama serve &' en otra sesión de Termux?" if IS_TERMUX else ""
            return {"type": "message", "content": f"❌ No se pudo conectar a Ollama en {OLLAMA_HOST}: {e}.{hint}"}
        msg = response["message"]
        state["messages"].append(msg)
        persist_state(state)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            return {"type": "message", "content": msg.get("content", "")}

        for call in tool_calls:
            fn_name = call["function"]["name"]
            fn_args = call["function"]["arguments"]
            if isinstance(fn_args, str):
                fn_args = json.loads(fn_args)

            if fn_name in DANGEROUS_ACTIONS:
                call_id = str(uuid.uuid4())
                state["pending"][call_id] = {"name": fn_name, "args": fn_args}
                return {
                    "type": "confirm",
                    "call_id": call_id,
                    "tool_name": fn_name,
                    "args": fn_args,
                }

            result = run_tool_now(tools, fn_name, fn_args)
            state["messages"].append({"role": "tool", "content": result})
            persist_state(state)
        # sigue el while: vuelve a llamar al modelo con los resultados agregados


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/history", methods=["GET"])
def history():
    """Devuelve el historial de la conversación actual (solo turnos de usuario/asistente
    con texto, para que el frontend los pinte al cargar la página)."""
    state = get_state()
    out = []
    for m in state["messages"]:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return jsonify({"messages": out})


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True)
    user_message = (data or {}).get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Mensaje vacío / Empty message"}), 400

    state = get_state()
    state["messages"].append({"role": "user", "content": user_message})
    persist_state(state)
    log_event("user_message", {"content": user_message})
    result = step_conversation(state)
    return jsonify(result)


@app.route("/api/confirm", methods=["POST"])
def confirm():
    data = request.get_json(force=True)
    call_id = data.get("call_id")
    approved = data.get("approved", False)

    state = get_state()
    pending = state["pending"].pop(call_id, None)
    if pending is None:
        return jsonify({"error": "No existe esa confirmación pendiente / No such pending confirmation"}), 400

    tools = load_all_tools()
    if approved:
        result = run_tool_now(tools, pending["name"], pending["args"])
    else:
        result = "El usuario canceló esta acción. / The user cancelled this action."

    state["messages"].append({"role": "tool", "content": result})
    persist_state(state)
    result = step_conversation(state)
    return jsonify(result)


@app.route("/api/reset", methods=["POST"])
def reset():
    state = get_state()
    state["messages"] = [{"role": "system", "content": SYSTEM_PROMPT}]
    state["pending"] = {}
    convstore.reset_conversation(session["sid"])
    return jsonify({"ok": True})


if __name__ == "__main__":
    print(f"🤖 Asistente corriendo en http://localhost:5000  (modelo: {MODEL}, ollama: {OLLAMA_HOST})")
    if IS_TERMUX:
        print("📱 Termux detectado. Si todavía no lo hiciste, abrí OTRA sesión de Termux")
        print("   y corré 'ollama serve &' antes de abrir la página.")
    app.run(host="0.0.0.0", port=5000, debug=False)
