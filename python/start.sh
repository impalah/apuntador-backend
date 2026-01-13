#!/bin/bash

# Script de inicio rápido para el backend OAuth

echo " Iniciando Apuntador OAuth Backend"
echo ""

# Verificar si existe .env
if [[ ! -f .env ]]; then
    echo "  No se encontró archivo .env"
    echo " Creando .env desde .env.example..."
    cp .env.example .env
    echo " Archivo .env creado"
    echo ""
    echo "  Por favor edita .env y configura tus credenciales OAuth"
    echo ""
    read -p "Presiona Enter para continuar cuando hayas configurado .env..."
fi

# Verificar si existe venv
if [[ ! -d "venv" ]]; then
    echo " Creando entorno virtual..."
    python3 -m venv venv
    echo " Entorno virtual creado"
fi

# Activar venv
echo " Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo " Instalando dependencias..."
pip install -r requirements.txt

echo ""
echo " ¡Todo listo!"
echo ""
echo "Para ejecutar el servidor:"
echo "  make dev"
echo ""
echo "O directamente:"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Documentación API estará en: http://localhost:8000/docs"
echo ""
