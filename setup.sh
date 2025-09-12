#!/bin/bash

echo "=== Configuración del Notificador de Séneca ==="

# Crear entorno virtual
echo "Creando entorno virtual..."
python3 -m venv venv

# Activar entorno virtual
echo "Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias de Python
echo "Instalando dependencias de Python..."
pip install -r requirements.txt

# Instalar ChromeDriver automáticamente
echo "Instalando ChromeDriver..."
python -c "
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Esto instalará automáticamente ChromeDriver
service = Service(ChromeDriverManager().install())
print('ChromeDriver instalado correctamente')
"

echo ""
echo "=== CONFIGURACIÓN NECESARIA ==="
echo ""
echo "1. Edita config.json con tus credenciales:"
echo "   - username: Tu usuario de Séneca"
echo "   - password: Tu contraseña de Séneca" 
echo ""
echo "2. Configura el bot de Telegram:"
echo "   - Crea un bot con @BotFather en Telegram"
echo "   - Obtén el token del bot"
echo "   - Obtén tu chat_id enviando un mensaje al bot y visitando:"
echo "     https://api.telegram.org/bot<TU_TOKEN>/getUpdates"
echo ""
echo "3. Para ejecutar manualmente:"
echo "   source venv/bin/activate"
echo "   python seneca_notifier.py"
echo ""
echo "4. Para automatizar, agrega a crontab (ejecutar cada 30 minutos):"
echo "   */30 * * * * cd $(pwd) && source venv/bin/activate && python seneca_notifier.py >> logs.txt 2>&1"
echo ""