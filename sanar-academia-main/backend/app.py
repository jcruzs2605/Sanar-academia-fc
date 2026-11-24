import os

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
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError
from utils import ValidationError, error_desde_excepcion, respuesta_error


def _url_base_de_datos():
    """Lee DATABASE_URL del entorno (Postgres en producción). Sin ella usa SQLite local."""
    url = os.environ.get('DATABASE_URL', '').strip()
    if url:
        # Algunos proveedores entregan 'postgres://', SQLAlchemy exige 'postgresql://'
        if url.startswith('postgres://'):
            url = url.replace('postgres://', 'postgresql://', 1)
        return url
    if os.environ.get('VERCEL'):
        # Respaldo para que la app no se caiga en Vercel: el disco es temporal, los datos NO persisten.
        print('[AVISO] Falta DATABASE_URL: se usa SQLite temporal en /tmp (los datos se perderán).')
        return 'sqlite:////tmp/futbol_app.db'
    return 'sqlite:///futbol_app.db'


def _inicializar_base_datos(app):
    """Crea las tablas y, si se define ADMIN_PASSWORD, el administrador inicial."""
    try:
        with app.app_context():
            db.create_all()
            password_admin = os.environ.get('ADMIN_PASSWORD')
            if password_admin and not Usuario.query.filter_by(nombre_usuario='admin').first():
                db.session.add(Usuario(
                    nombre_usuario='admin',
                    password=generate_password_hash(password_admin),
                    rol='admin',
                    nombre_completo='Administrador Principal'
                ))
                db.session.commit()
                print('[OK] Administrador inicial creado (usuario: admin).')
    except Exception as e:
        print(f'[ERROR] No se pudo inicializar la base de datos: {e}')


def create_app():
    app = Flask(__name__)

    app.config['SQLALCHEMY_DATABASE_URI'] = _url_base_de_datos()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
    # En producción define SECRET_KEY en las variables de entorno (el valor por defecto es solo para desarrollo)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mi_secreto_super_seguro')

    # Cookies de sesión: en producción (HTTPS) activar COOKIE_SECURE=1
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('COOKIE_SECURE', '0') == '1'
    app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('COOKIE_SAMESITE', 'Lax')

    # Orígenes permitidos (separados por coma). Con el proxy de Render no se necesita,
    # pero sirve si el front llama directamente al backend.
    origenes = [o.strip() for o in os.environ.get(
        'CORS_ORIGINS', 'http://localhost:4200,http://127.0.0.1:4200'
    ).split(',') if o.strip()]
    CORS(
        app,
        resources={r"/*": {"origins": origenes}},
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

    # En Vercel (serverless) no hay un paso previo de "python run.py": las tablas se crean al arrancar
    if os.environ.get('VERCEL') or os.environ.get('AUTO_CREATE_DB') == '1':
        _inicializar_base_datos(app)

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
