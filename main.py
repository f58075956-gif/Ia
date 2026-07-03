"""
Asistente personal local con Ollama.
Correlo con: python main.py [nombre_de_sesion]

La conversación se guarda en data/conversations/<nombre_de_sesion>.json y se
retoma automáticamente la próxima vez que corras el script. Si querés varias
conversaciones separadas, pasale un nombre distinto como argumento.
"""
import json
import sys

try:
    import ollama
except ImportError:
    print("Falta instalar la librería 'ollama'. Corré: pip install ollama")
    sys.exit(1)

from config import MODEL, SYSTEM_PROMPT, DANGEROUS_ACTIONS, OLLAMA_HOST, IS_TERMUX, MAX_TOOL_ITERATIONS
from tools.loader import load_all_tools, to_ollama_schema
from activity_log import log_event
import conversation_store as convstore

# Cliente explícito apuntando a OLLAMA_HOST (respeta la variable de entorno
# del mismo nombre si se seteó, o localhost:11434 por defecto).
client = ollama.Client(host=OLLAMA_HOST)

SESSION_ID = sys.argv[1] if len(sys.argv) > 1 else "cli"


def ask_confirmation(tool_name: str, args: dict) -> bool:
    print(f"\n⚠️  El asistente quiere ejecutar / The assistant wants to run: {tool_name}({args})")
    resp = input("¿Confirmás? / Confirm? [s/y = sí/yes, cualquier otra tecla = no]: ").strip().lower()
    return resp in ("s", "si", "sí", "y", "yes")


def run_tool(tools: dict, name: str, args: dict) -> str:
    if name not in tools:
        return f"Herramienta '{name}' no existe."

    if name in DANGEROUS_ACTIONS:
        if not ask_confirmation(name, args):
            return "El usuario canceló esta acción."

    try:
        result = str(tools[name]["fn"](**args))
    except Exception as e:
        result = f"Error ejecutando '{name}': {e}"
    log_event("tool_call", {"name": name, "args": args, "result": result[:300]})
    return result


def chat_loop():
    print(f"🤖 Asistente local corriendo con el modelo '{MODEL}' ({OLLAMA_HOST}).")
    if IS_TERMUX:
        print("📱 Termux detectado. Si todavía no lo hiciste, abrí OTRA sesión de Termux")
        print("   y corré 'ollama serve &' antes de usar el asistente.")

    # Retoma la conversación guardada si existe. El primer mensaje (system
    # prompt) se pisa siempre con el SYSTEM_PROMPT actual, así los cambios en
    # config.py se aplican aunque haya una conversación vieja guardada.
    loaded = convstore.load_conversation(SESSION_ID)
    if loaded:
        messages = loaded
        messages[0] = {"role": "system", "content": SYSTEM_PROMPT}
        n_turns = sum(1 for m in messages if m.get("role") == "user")
        print(f"💾 Conversación '{SESSION_ID}' retomada ({n_turns} mensajes previos). "
              f"/ Resumed conversation '{SESSION_ID}' ({n_turns} previous messages).")
    else:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("Escribí 'salir' para terminar, o 'nueva' para empezar de cero. / "
          "Type 'exit' to quit, or 'new' to start over.\n")

    def persist():
        convstore.save_conversation(SESSION_ID, messages)

    while True:
        tools = load_all_tools()  # recarga por si se creó una herramienta nueva
        ollama_tools = to_ollama_schema(tools)

        user_input = input("Vos: ").strip()
        if user_input.lower() in ("salir", "exit", "quit"):
            print("Chau! 👋")
            break
        if user_input.lower() in ("nueva", "nuevo", "new", "reset"):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            convstore.reset_conversation(SESSION_ID)
            print("🧹 Conversación reiniciada. / Conversation reset.\n")
            continue
        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})
        persist()
        log_event("user_message", {"content": user_input})

        # Loop de tool-calling: puede encadenar varias herramientas antes de responder
        iterations = 0
        while True:
            iterations += 1
            if iterations > MAX_TOOL_ITERATIONS:
                print(f"\n⚠️  Se alcanzó el límite de {MAX_TOOL_ITERATIONS} llamadas a "
                      f"herramientas encadenadas para este mensaje. Cortando para evitar un loop.\n")
                break
            try:
                response = client.chat(model=MODEL, messages=messages, tools=ollama_tools)
            except Exception as e:
                print(f"\n❌ No se pudo conectar a Ollama en {OLLAMA_HOST}: {e}")
                print(f"   Could not connect to Ollama at {OLLAMA_HOST}: {e}")
                if IS_TERMUX:
                    print("   ¿Corriste 'ollama serve &' en otra sesión de Termux? / "
                          "Did you run 'ollama serve &' in another Termux session?")
                messages.pop()  # saca el user_input fallido para poder reintentar
                persist()
                break
            msg = response["message"]
            messages.append(msg)
            persist()

            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                print(f"\nAsistente: {msg.get('content', '')}\n")
                break

            for call in tool_calls:
                fn_name = call["function"]["name"]
                fn_args = call["function"]["arguments"]
                if isinstance(fn_args, str):
                    fn_args = json.loads(fn_args)

                result = run_tool(tools, fn_name, fn_args)
                messages.append({
                    "role": "tool",
                    "content": result,
                })
                persist()


if __name__ == "__main__":
    chat_loop()
