from flask import Flask, request, jsonify
from flask_cors import CORS
from models.models import db, Usuario
from routes.auth import auth_bp
from routes.main import main_bp
from routes.admin import admin_bp
from routes.profesores import profesor_bp
from routes.acudientes import acudiente_bp
from routes.avisos import avisos_bp
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from utils import ValidationError, error_desde_excepcion, respuesta_error

def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///futbol_app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'mi_secreto_super_seguro'

    # Configuración de CORS corregida para permitir credenciales/sesiones
    CORS(
        app,
        resources={r"/*": {"origins": ["http://localhost:4200", "http://127.0.0.1:4200"]}},
        supports_credentials=True
    )

    db.init_app(app)

    # Registramos los blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(profesor_bp, url_prefix='/api/profesor')
    app.register_blueprint(acudiente_bp, url_prefix='/api/acudiente')
    app.register_blueprint(avisos_bp, url_prefix='/api/avisos')

    # ---- Manejo global de errores: siempre JSON con mensaje en español ----
    @app.errorhandler(ValidationError)
    def _validacion(e):
        return error_desde_excepcion(e)

    @app.errorhandler(SQLAlchemyError)
    def _base_datos(e):
        return error_desde_excepcion(e, db)

    @app.errorhandler(HTTPException)
    def _http(e):
        mensajes = {
            400: 'La solicitud no es válida. Revisa los datos enviados.',
            401: 'Debes iniciar sesión para continuar.',
            403: 'No tienes permisos para realizar esta acción.',
            404: 'No se encontró el registro solicitado. Es posible que haya sido eliminado.',
            405: 'Operación no permitida para este recurso.',
            415: 'El formato de los datos enviados no es válido.',
        }
        return respuesta_error(mensajes.get(e.code, e.description or 'Error en la solicitud.'), e.code or 500)

    @app.errorhandler(Exception)
    def _generico(e):
        return error_desde_excepcion(e, db)

    @app.route('/api/ping', methods=['GET'])
    def ping():
        return jsonify({"mensaje": "API de Flask funcionando correctamente"}), 200

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)