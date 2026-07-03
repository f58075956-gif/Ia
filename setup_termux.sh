#!/data/data/com.termux/files/usr/bin/bash
# Instala todo lo necesario para correr el asistente en Termux (Android).
# Uso: bash setup_termux.sh
set -e

if [ "$PREFIX" != *"com.termux"* ] && [ -z "$PREFIX" ]; then
    echo "⚠️  Esto no parece ser Termux. Corré este script dentro de Termux."
fi

echo "📦 Actualizando paquetes..."
pkg update -y && pkg upgrade -y

echo "📦 Instalando Python, Ollama y dependencias de compilación..."
pkg install -y python ollama clang

echo "🔓 Dando acceso al almacenamiento (opcional, para leer/escribir fuera de Termux)..."
termux-setup-storage || true

echo "📦 Instalando dependencias de Python..."
pip install --upgrade pip
pip install -r "$(dirname "$0")/requirements.txt"

echo ""
echo "✅ Listo. Para usar el asistente:"
echo "   1) En una sesión de Termux: ollama serve &"
echo "   2) En otra sesión:          ollama pull llama3.2:3b"
echo "   3) Y después:                python main.py   (o python webapp/server.py)"
echo ""
echo "💡 Tip: corré 'termux-wake-lock' antes de sesiones largas para que Android"
echo "   no mate el proceso en segundo plano."
