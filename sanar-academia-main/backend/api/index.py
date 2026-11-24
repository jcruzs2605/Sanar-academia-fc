"""Punto de entrada para Vercel (Python serverless). Vercel busca la variable `app`."""
import os
import sys

# Permite importar app.py, models/, routes/ y utils.py desde la carpeta backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402

app = create_app()
