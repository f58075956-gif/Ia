"""Herramientas de acceso a internet."""
import os
import re
import sys
import requests

# El paquete se renombró de "duckduckgo_search" a "ddgs". Probamos ambos para
# que funcione con cualquiera de las dos versiones instaladas (en Termux a
# veces sólo hay disponible una de las dos vía pip).
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DOWNLOADS_DIR

USER_AGENT = "Mozilla/5.0 (compatible; AsistentePersonal/1.0)"
MAX_CHARS = 6000  # límite para no saturar el contexto del modelo


def web_search(query: str, max_results: int = 5) -> str:
    """Busca en internet (DuckDuckGo) y devuelve título, resumen y link de cada resultado."""
    if DDGS is None:
        return "Falta instalar el buscador. Corré: pip install ddgs (o duckduckgo-search)"
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    f"- {r.get('title')}\n  {r.get('href')}\n  {r.get('body', '')[:200]}"
                )
        if not results:
            return "No se encontraron resultados."
        return "\n\n".join(results)
    except Exception as e:
        return f"Error buscando en internet: {e}"


def _extract_text(html: str) -> str:
    # extracción simple sin dependencias pesadas: saca tags y espacios de sobra
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def web_fetch(url: str) -> str:
    """Descarga una página web y devuelve su contenido en texto plano (recortado)."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
        resp.raise_for_status()
        text = _extract_text(resp.text)
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + f"\n\n[... contenido recortado, {len(text)} caracteres en total ...]"
        return text
    except Exception as e:
        return f"Error accediendo a la URL: {e}"


def download_file(url: str, filename: str) -> str:
    """Descarga un archivo de internet y lo guarda en la carpeta downloads/."""
    safe_name = os.path.basename(filename or "").strip()
    if not safe_name:
        return "Error: el nombre de archivo quedó vacío. Especificá un filename válido."

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    path = os.path.join(DOWNLOADS_DIR, safe_name)
    total = 0
    try:
        with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=30) as r:
            r.raise_for_status()
            max_bytes = 200 * 1024 * 1024  # límite de seguridad: 200MB
            with open(path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    total += len(chunk)
                    if total > max_bytes:
                        f.close()
                        os.remove(path)
                        return "Error: el archivo supera el límite de 200MB permitido."
                    f.write(chunk)
        return f"Archivo descargado en {path} ({total/1024:.1f} KB)"
    except Exception as e:
        # Si algo falló a mitad de la descarga (conexión cortada, timeout, etc.)
        # no dejamos un archivo parcial/corrupto tirado en downloads/.
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass
        return f"Error descargando el archivo: {e}"


WEB_TOOLS = {
    "web_search": {
        "fn": web_search,
        "description": "Busca información actual en internet. Devuelve título, link y resumen de cada resultado.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Qué buscar"},
                "max_results": {"type": "integer", "description": "Cantidad de resultados (default 5)"},
            },
            "required": ["query"],
        },
    },
    "web_fetch": {
        "fn": web_fetch,
        "description": "Abre una URL específica y devuelve el texto de la página, para leer un artículo o sitio puntual.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    "download_file": {
        "fn": download_file,
        "description": "Descarga un archivo desde una URL y lo guarda en la carpeta downloads/. Pide confirmación.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "filename": {"type": "string", "description": "Nombre con el que guardarlo"},
            },
            "required": ["url", "filename"],
        },
    },
}
