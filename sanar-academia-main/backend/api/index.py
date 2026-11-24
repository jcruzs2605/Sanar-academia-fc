"""Punto de entrada para Vercel (Python serverless). Vercel busca la variable `app`."""
import os
import sys
import traceback

# Permite importar app.py, models/, routes/ y utils.py desde la carpeta backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app import create_app  # noqa: E402

    app = create_app()
except Exception as _error:  # pragma: no cover
    # Si el arranque falla, se deja la causa en los logs y se responde con un JSON claro
    # (solo el tipo de error, sin datos sensibles) en lugar de un 500 sin explicación.
    traceback.print_exc()
    from flask import Flask, jsonify

    _tipo = type(_error).__name__
    app = Flask(__name__)

    @app.route('/', defaults={'ruta': ''})
    @app.route('/<path:ruta>')
    def _fallo_de_arranque(ruta):
        return jsonify({
            'error': 'El servidor no pudo iniciar. Revisa las variables de entorno y los logs de Vercel.',
            'tipo': _tipo
        }), 500
