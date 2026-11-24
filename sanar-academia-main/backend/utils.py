"""Utilidades de validación y mensajes de error legibles para el usuario."""
from datetime import datetime, date
from flask import jsonify


class ValidationError(Exception):
    """Error de validación con mensaje listo para mostrar al usuario."""

    def __init__(self, mensaje, status=400, campos=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.status = status
        self.campos = campos or []


def respuesta_error(mensaje, status=400, campos=None):
    cuerpo = {'error': mensaje}
    if campos:
        cuerpo['campos'] = campos
    return jsonify(cuerpo), status


def texto(data, campo):
    valor = data.get(campo)
    return valor.strip() if isinstance(valor, str) else ''


def exigir_campos(data, etiquetas):
    """etiquetas: {'campo': 'Etiqueta legible'}. Lanza error listando TODO lo que falta."""
    faltantes = []
    for campo, etiqueta in etiquetas.items():
        valor = data.get(campo)
        if valor is None or (isinstance(valor, str) and not valor.strip()) \
                or (isinstance(valor, (list, tuple)) and not valor):
            faltantes.append((campo, etiqueta))
    if faltantes:
        nombres = ', '.join(e for _, e in faltantes)
        if len(faltantes) == 1:
            msg = f'Falta completar el campo: {nombres}.'
        else:
            msg = f'Faltan campos por completar: {nombres}.'
        raise ValidationError(msg, 400, [c for c, _ in faltantes])


def a_entero(valor, etiqueta):
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValidationError(f'El campo "{etiqueta}" no es válido.')


def a_numero(valor, etiqueta, minimo=None, maximo=None, unidad=''):
    try:
        numero = float(str(valor).replace(',', '.'))
    except (TypeError, ValueError):
        raise ValidationError(f'El campo "{etiqueta}" debe ser un número.')
    if minimo is not None and numero < minimo:
        raise ValidationError(f'"{etiqueta}" no puede ser menor que {minimo}{unidad}.')
    if maximo is not None and numero > maximo:
        raise ValidationError(f'"{etiqueta}" no puede ser mayor que {maximo}{unidad}.')
    return numero


def a_fecha(valor, etiqueta, permitir_futuro=True):
    try:
        fecha = datetime.strptime(str(valor).strip()[:10], '%Y-%m-%d').date()
    except ValueError:
        raise ValidationError(f'"{etiqueta}" no tiene un formato válido (use AAAA-MM-DD).')
    if not permitir_futuro and fecha > date.today():
        raise ValidationError(f'"{etiqueta}" no puede ser una fecha futura.')
    return fecha


def a_fecha_hora(valor, etiqueta):
    texto_valor = str(valor).strip()
    for formato in ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return datetime.strptime(texto_valor, formato)
        except ValueError:
            continue
    raise ValidationError(f'La fecha y hora de "{etiqueta}" no tienen un formato válido.')


def traducir_error_bd(error):
    """Convierte errores técnicos de SQLite/SQLAlchemy en mensajes comprensibles."""
    detalle = str(getattr(error, 'orig', error)).lower()
    if 'unique' in detalle:
        if 'nombre_usuario' in detalle:
            return 'Ese nombre de usuario ya está registrado. Elige otro.'
        return 'Ya existe un registro con esos datos. Verifica que no esté duplicado.'
    if 'not null' in detalle:
        campo = detalle.split('.')[-1].replace('_', ' ').strip() if '.' in detalle else 'un campo obligatorio'
        return f'Falta información obligatoria en la base de datos ({campo}). Completa todos los campos.'
    if 'foreign key' in detalle:
        return ('No se puede completar la operación porque el registro depende de otro que no existe '
                'o tiene información asociada (por ejemplo jugadores, pagos o eventos).')
    if 'locked' in detalle:
        return 'La base de datos está ocupada en este momento. Intenta de nuevo en unos segundos.'
    return 'Ocurrió un problema al guardar la información en la base de datos. Intenta de nuevo.'


def error_desde_excepcion(e, db=None, contexto='completar la operación'):
    """Devuelve (respuesta JSON) legible para cualquier excepción y hace rollback si se pasa db."""
    from sqlalchemy.exc import SQLAlchemyError
    from werkzeug.exceptions import HTTPException
    if db is not None:
        try:
            db.session.rollback()
        except Exception:
            pass
    if isinstance(e, ValidationError):
        return respuesta_error(e.mensaje, e.status, e.campos)
    if isinstance(e, HTTPException):
        mensajes = {
            400: 'La solicitud no es válida. Revisa los datos enviados.',
            401: 'Debes iniciar sesión para continuar.',
            403: 'No tienes permisos para realizar esta acción.',
            404: 'No se encontró el registro solicitado. Es posible que haya sido eliminado.',
            405: 'Operación no permitida para este recurso.',
            415: 'El formato de los datos enviados no es válido.',
        }
        return respuesta_error(mensajes.get(e.code, e.description or 'Error en la solicitud.'), e.code or 500)
    if isinstance(e, SQLAlchemyError):
        print(f'[DB] Error al {contexto}: {e}')
        estado = 409 if 'unique' in str(e).lower() else 400
        return respuesta_error(traducir_error_bd(e), estado)
    print(f'[ERROR] No se pudo {contexto}: {e!r}')
    return respuesta_error(f'No se pudo {contexto}. Intenta de nuevo; si persiste, contacta al administrador.', 500)
