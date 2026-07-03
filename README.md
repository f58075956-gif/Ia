# Asistente Personal Local

Un asistente que corre 100% en tu compu (sin API paga, sin internet para el modelo),
con memoria persistente, herramientas (archivos, código, terminal) y la capacidad de
**crearse nuevas herramientas a sí mismo** cuando las necesita.

## 1. Instalar Ollama (el motor que corre el modelo localmente)

Descargá e instalá desde: https://ollama.com/download

Verificá que funciona:
```bash
ollama --version
```

## 2. Descargar un modelo

Con tu GPU, recomiendo empezar con este (8B, rápido y soporta herramientas):
```bash
ollama pull llama3.1
```

Alternativas si querés más calidad (necesita más VRAM):
```bash
ollama pull qwen2.5:14b
```

Si cambiás de modelo, actualizá `MODEL` en `config.py`.

## 3. Instalar dependencias de Python

```bash
pip install -r requirements.txt
```

### ¿Instalando en Termux (Android)?

Este proyecto también corre en Termux. Hay un script que hace todo el paso 1-3
de una: `bash setup_termux.sh` (instala Ollama, Python, dependencias y da
acceso al almacenamiento). Después seguí desde el paso 4 de acá abajo, con
estas diferencias:

- Usá un modelo liviano: `ollama pull llama3.2:3b` (o `llama3.2:1b` si tu
  celular tiene poca RAM). El asistente detecta que está en Termux y usa
  `llama3.2:3b` por defecto automáticamente — no hace falta tocar `config.py`.
- Ollama no arranca solo: abrí una sesión de Termux y corré `ollama serve &`
  antes de usar el asistente (dejala abierta).
- Corré `termux-wake-lock` antes de sesiones largas para que Android no mate
  el proceso en segundo plano.
- Guardá y corré todo desde el home de Termux (`~`), nunca desde `/sdcard`,
  o vas a tener errores de permisos.
- Si querés otro modelo o que Ollama escuche en otra dirección, seteá las
  variables de entorno `ASSISTANT_MODEL` y `OLLAMA_HOST` en vez de editar
  `config.py`, por ejemplo:
  ```bash
  export ASSISTANT_MODEL=qwen2.5:1.5b
  python main.py
  ```

## 4. Correr el asistente

Primero asegurate que Ollama esté corriendo (normalmente arranca solo, o corré `ollama serve`).

**Opción A — Terminal:**
```bash
python main.py
```

**Opción B — Interfaz web (recomendada, tipo chat visual):**
```bash
python webapp/server.py
```
Después abrí **http://localhost:5000** en tu navegador. Vas a ver una interfaz de
chat con burbujas de mensaje, indicador de "escribiendo", y tarjetas de confirmación
que aparecen inline cuando el asistente quiere ejecutar algo riesgoso (código, comandos,
crear una herramienta nueva) — apretás "Permitir" o "Cancelar" ahí mismo.

## Cómo funciona

- **`config.py`**: acá cambiás el modelo, el prompt del sistema, y qué acciones piden confirmación.
- **`conversation_store.py`**: guarda la conversación completa (no solo la memoria
  key-value) en `data/conversations/<sesión>.json` después de cada mensaje. Si
  reiniciás `main.py` o `webapp/server.py`, retoma la charla donde quedó. En
  terminal podés tener conversaciones separadas con `python main.py <nombre>`;
  escribí `nueva` en cualquier momento para empezar de cero. En la webapp cada
  pestaña/navegador tiene su propia conversación persistida (por cookie de
  sesión), y el botón "Nueva conversación" también borra el archivo guardado.
- **`memory.py`**: memoria persistente en `data/memory.json`. El asistente puede guardar y
  recordar datos entre sesiones con `remember` / `recall`.
- **`activity_log.py`**: registra automáticamente todo lo que hace (mensajes, herramientas
  usadas, resultados) en `data/activity_log.jsonl`. El asistente puede revisarlo con
  `review_own_activity` para notar tareas repetidas y decidir crearse una herramienta
  nueva que las resuelva mejor — así es como "mejora" con el tiempo.
- **`tools/builtin.py`**: herramientas base (archivos, código, terminal, memoria, auto-revisión).
- **`tools/web.py`**: herramientas de internet — `web_search` (busca en DuckDuckGo, sin
  necesitar API key), `web_fetch` (lee el contenido de una URL puntual), `download_file`
  (descarga archivos a la carpeta `downloads/`, con límite de 200MB y confirmación previa).
- **`dynamic_tools/`**: acá van a parar las herramientas que el asistente se crea a sí mismo
  con `create_tool`. Se cargan automáticamente en cada mensaje nuevo — no hace falta
  reiniciar nada.
- **`main.py`** / **`webapp/server.py`**: los dos loops de conversación (terminal y web).

## Cómo "mejora solo"

No hay magia: no se reentrena a sí mismo ni cambia su propio modelo. Lo que sí hace:
1. Cada acción queda registrada en `data/activity_log.jsonl`.
2. Cuando le pedís algo, o de tanto en tanto vos mismo le podés decir "revisá tu actividad
   reciente y fijate si conviene crear alguna herramienta nueva", usa `review_own_activity`
   para mirar el patrón de lo que viene haciendo.
3. Si detecta que repite una tarea manualmente, usa `create_tool` para escribirse una
   función que la resuelva de forma más directa la próxima vez.

Es un ciclo simple pero real: cuantas más herramientas se va creando, menos tiene que
improvisar con `run_python` para tareas que ya resolvió antes.

## Seguridad — leer antes de usar

Este asistente puede ejecutar código y comandos en tu compu. Por diseño:
- Las acciones riesgosas (`run_python`, `run_shell`, `create_tool`, `delete_file`)
  **siempre** piden tu confirmación explícita antes de ejecutarse.
- Podés editar `DANGEROUS_ACTIONS` en `config.py` para agregar o sacar herramientas
  de esa lista según qué tan cómodo te sientas.
- Recomiendo correrlo primero en una carpeta de pruebas, no directamente sobre
  archivos importantes, hasta que le agarres confianza.
- El acceso a internet (`web_search`, `web_fetch`) es de solo lectura y no pide
  confirmación por defecto. `download_file` sí la pide, y tiene un límite de 200MB
  por archivo. Si querés que `web_fetch` también pida confirmación (por ejemplo,
  si te preocupa que visite sitios no deseados), agregalo a `DANGEROUS_ACTIONS`
  en `config.py`.

## Sobre la veracidad de las respuestas

El asistente está instruido para buscar en internet (`web_search`/`web_fetch`)
**antes** de responder cualquier cosa que dependa de datos actuales, cifras,
fechas o hechos verificables, en vez de contestar de memoria — y para decir
explícitamente cuando las fuentes no coinciden o no encontró nada confiable,
en vez de inventar. Dicho eso, **no hay forma de garantizar que sea 100%
verídico**: sigue siendo un modelo de lenguaje que puede malinterpretar una
fuente, y la calidad de la respuesta depende de qué tan bueno sea el modelo
que elegiste (`config.py` / `ASSISTANT_MODEL`) y de qué tan buenas sean las
fuentes que encuentre. Para decisiones importantes, revisá siempre los links
que cita.

## Ejemplos de uso

```
Vos: Recordá que mi reunión con el equipo es todos los lunes a las 10am
Vos: ¿Qué tengo guardado en la memoria?
Vos: Creá una herramienta que convierta un texto a mayúsculas
Vos: Leé el archivo notas.txt y resumímelo
Vos: Buscá en internet las últimas noticias sobre energía solar
Vos: Descargame el PDF de esa página
Vos: Revisá tu actividad reciente, ¿hay algo que convenga automatizar?
```

## Extender el asistente

Para agregarle una herramienta vos mismo (sin pasar por el chat), creá un archivo
en `dynamic_tools/mi_herramienta.py`:

```python
"""Descripción de qué hace la herramienta."""

TOOL_SCHEMA = {
    "type": "object",
    "properties": {"texto": {"type": "string"}},
    "required": ["texto"],
}

def mi_herramienta(texto: str) -> str:
    return texto.upper()
```

Se carga automáticamente la próxima vez que corras `main.py` (o en el próximo mensaje,
ya que el loop recarga las herramientas en cada turno).
