from flask import Blueprint, jsonify, request
from models.models import db, Usuario, Categoria, Jugador, Pago, Evento, Aviso
from datetime import datetime
from werkzeug.security import generate_password_hash
from utils import (
    ValidationError, exigir_campos, texto, a_entero, a_numero, a_fecha,
    error_desde_excepcion
)

ESTADOS_PAGO = ('Pendiente', 'Pagado', 'Atrasado')
ROLES_VALIDOS = ('admin', 'profesor', 'acudiente')
POSICIONES_VALIDAS = ('Portero', 'Defensa', 'Mediocampista', 'Centrocampista', 'Delantero')


def normalizar_estado(estado):
    """Unifica los estados antiguos ('Completado') con los del backlog."""
    valor = (estado or 'Pendiente').strip().capitalize()
    if valor in ('Completado', 'Pagada'):
        return 'Pagado'
    if valor in ('Vencido',):
        return 'Atrasado'
    return valor if valor in ESTADOS_PAGO else 'Pendiente'


def validar_jugador(data, id_actual=None):
    """Valida que TODA la información del jugador esté completa y sea correcta."""
    exigir_campos(data, {
        'nombre': 'Nombre del jugador',
        'fecha_nacimiento': 'Fecha de nacimiento',
        'estatura': 'Estatura',
        'peso': 'Peso',
        'posicion': 'Posición',
        'acudiente_id': 'Acudiente',
        'categoria_id': 'Categoría',
    })
    nombre = texto(data, 'nombre')
    if len(nombre) < 3:
        raise ValidationError('El nombre del jugador debe tener al menos 3 caracteres.')
    if len(nombre) > 100:
        raise ValidationError('El nombre del jugador no puede superar los 100 caracteres.')

    fecha = a_fecha(data.get('fecha_nacimiento'), 'Fecha de nacimiento', permitir_futuro=False)
    if (datetime.now().date() - fecha).days > 365 * 25:
        raise ValidationError('La fecha de nacimiento no es válida para un jugador de la escuela.')

    # Estatura en metros o centímetros; peso en kilos
    estatura = a_numero(data.get('estatura'), 'Estatura', minimo=0.5, maximo=250)
    peso = a_numero(data.get('peso'), 'Peso', minimo=10, maximo=200, unidad=' kg')

    posicion = texto(data, 'posicion')
    if posicion not in POSICIONES_VALIDAS:
        raise ValidationError(f'La posición debe ser una de: {", ".join(POSICIONES_VALIDAS)}.')

    acudiente_id = a_entero(data.get('acudiente_id'), 'Acudiente')
    acudiente = Usuario.query.get(acudiente_id)
    if not acudiente or acudiente.rol != 'acudiente':
        raise ValidationError('El acudiente seleccionado no existe o no tiene rol de acudiente.')

    categoria_id = a_entero(data.get('categoria_id'), 'Categoría')
    if not Categoria.query.get(categoria_id):
        raise ValidationError('La categoría seleccionada no existe.')

    return {
        'nombre': nombre, 'fecha_nacimiento': fecha, 'estatura': estatura, 'peso': peso,
        'posicion': posicion, 'acudiente_id': acudiente_id, 'categoria_id': categoria_id
    }


admin_bp = Blueprint('admin', __name__)

# ==========================================
# DASHBOARD
# ==========================================
@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    pagos = Pago.query.all()
    pendientes = [p for p in pagos if normalizar_estado(p.estado) != 'Pagado']
    conteo = {
        'usuarios': Usuario.query.count(),
        'jugadores': Jugador.query.count(),
        'categorias': Categoria.query.count(),
        'profesores': Usuario.query.filter_by(rol='profesor').count(),
        'acudientes': Usuario.query.filter_by(rol='acudiente').count(),
        'eventos': Evento.query.count(),
        'avisos': Aviso.query.count(),
        'pagos_pendientes': len(pendientes),
        'valor_pendiente': sum(float(p.monto or 0) for p in pendientes),
        'recaudado': sum(float(p.monto or 0) for p in pagos if normalizar_estado(p.estado) == 'Pagado')
    }
    return jsonify(conteo), 200


# ==========================================
# GESTIÓN DE USUARIOS
# ==========================================
@admin_bp.route('/usuarios', methods=['GET'])
def listar_usuarios():
    usuarios = Usuario.query.all()
    resultado = [{
        'id': u.id,
        'nombre_usuario': u.nombre_usuario,
        'nombre_completo': u.nombre_completo,
        'rol': u.rol
    } for u in usuarios]
    return jsonify(resultado), 200


def validar_usuario(data, id_actual=None, password_obligatoria=True):
    campos = {'nombre': 'Nombre completo', 'username': 'Nombre de usuario', 'rol': 'Rol'}
    if password_obligatoria:
        campos['password'] = 'Contraseña'
    exigir_campos(data, campos)

    nombre = texto(data, 'nombre')
    username = texto(data, 'username')
    rol = texto(data, 'rol')

    if len(nombre) < 3:
        raise ValidationError('El nombre completo debe tener al menos 3 caracteres.')
    if len(username) < 3 or ' ' in username:
        raise ValidationError('El nombre de usuario debe tener al menos 3 caracteres y no puede contener espacios.')
    if rol not in ROLES_VALIDOS:
        raise ValidationError('El rol seleccionado no es válido. Usa administrador, profesor o acudiente.')

    password = data.get('password') or ''
    if password and len(password) < 6:
        raise ValidationError('La contraseña debe tener al menos 6 caracteres.')

    existente = Usuario.query.filter_by(nombre_usuario=username).first()
    if existente and existente.id != id_actual:
        raise ValidationError('Ese nombre de usuario ya existe. Elige otro.', 409, ['username'])
    return nombre, username, rol, password


@admin_bp.route('/usuarios/nuevo', methods=['POST'])
def crear_usuario():
    try:
        data = request.get_json(silent=True) or {}
        nombre, username, rol, password = validar_usuario(data)
        nuevo_user = Usuario(
            nombre_usuario=username,
            password=generate_password_hash(password),
            rol=rol,
            nombre_completo=nombre
        )
        db.session.add(nuevo_user)
        db.session.commit()
        return jsonify({'mensaje': 'Usuario creado exitosamente'}), 201
    except Exception as e:
        return error_desde_excepcion(e, db, 'crear el usuario')


@admin_bp.route('/usuarios/editar/<int:id>', methods=['PUT'])
def editar_usuario(id):
    try:
        usuario = Usuario.query.get_or_404(id)
        data = request.get_json(silent=True) or {}
        # Si no se envía un campo, se conserva el actual (la contraseña es opcional al editar)
        combinado = {
            'nombre': data.get('nombre', usuario.nombre_completo),
            'username': data.get('username', usuario.nombre_usuario),
            'rol': data.get('rol', usuario.rol),
            'password': data.get('password')
        }
        nombre, username, rol, password = validar_usuario(combinado, id_actual=id, password_obligatoria=False)

        if usuario.nombre_usuario == 'admin' and (username != 'admin' or rol != 'admin'):
            raise ValidationError('No puedes cambiar el usuario ni el rol del administrador principal.')

        usuario.nombre_completo = nombre
        usuario.nombre_usuario = username
        usuario.rol = rol
        if password:  # Solo cambia si se envía un valor
            usuario.password = generate_password_hash(password)

        db.session.commit()
        return jsonify({'mensaje': 'Usuario actualizado correctamente'}), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'actualizar el usuario')


@admin_bp.route('/usuarios/eliminar/<int:id>', methods=['DELETE'])
def eliminar_usuario(id):
    try:
        usuario = Usuario.query.get_or_404(id)
        if usuario.nombre_usuario == 'admin':
            raise ValidationError('No puedes eliminar al administrador principal.')
        if usuario.rol == 'acudiente' and usuario.hijos:
            raise ValidationError(
                f'No se puede eliminar: el acudiente tiene {len(usuario.hijos)} jugador(es) asociado(s). '
                'Reasigna o elimina primero a los jugadores.', 409)
        if usuario.rol == 'profesor' and usuario.categorias_dirigidas:
            raise ValidationError(
                f'No se puede eliminar: el profesor dirige {len(usuario.categorias_dirigidas)} categoría(s). '
                'Asigna otro entrenador a esas categorías primero.', 409)

        db.session.delete(usuario)
        db.session.commit()
        return jsonify({'mensaje': 'Usuario eliminado correctamente'}), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'eliminar el usuario')

# ==========================================
# GESTIÓN DE JUGADORES
# ==========================================
@admin_bp.route('/jugadores', methods=['GET'])
def listar_jugadores():
    try:
        jugadores = Jugador.query.all()
        resultado = []
        for j in jugadores:
            acudiente_nom = j.acudiente.nombre_completo if hasattr(j, 'acudiente') and j.acudiente else 'Sin Acudiente'
            categoria_nom = j.categoria_rel.nombre if hasattr(j, 'categoria_rel') and j.categoria_rel else 'Sin Categoría'

            resultado.append({
                'id': j.id,
                'nombre': j.nombre,
                'fecha_nacimiento': j.fecha_nacimiento.strftime('%Y-%m-%d') if j.fecha_nacimiento else None,
                'estatura': j.estatura,
                'peso': j.peso,
                'posicion': j.posicion,
                'acudiente_id': j.acudiente_id,
                'acudiente': acudiente_nom,
                'categoria_id': j.categoria_id,
                'categoria': categoria_nom
            })
        return jsonify(resultado), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'cargar la lista de jugadores')


# OBTENER JUGADOR POR ID (Necesario para cargar el formulario de edición)
@admin_bp.route('/jugadores/<int:id>', methods=['GET'])
def obtener_jugador(id):
    try:
        jugador = Jugador.query.get_or_404(id)
        return jsonify({
            'id': jugador.id,
            'nombre': jugador.nombre,
            'fecha_nacimiento': jugador.fecha_nacimiento.strftime('%Y-%m-%d') if jugador.fecha_nacimiento else '',
            'estatura': jugador.estatura,
            'peso': jugador.peso,
            'posicion': jugador.posicion or '',
            'acudiente_id': jugador.acudiente_id,
            'categoria_id': jugador.categoria_id
        }), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'cargar los datos del jugador')


@admin_bp.route('/jugadores/nuevo', methods=['POST'])
def crear_jugador():
    try:
        datos = validar_jugador(request.get_json(silent=True) or {})
        db.session.add(Jugador(**datos))
        db.session.commit()
        return jsonify({'mensaje': 'Jugador inscrito correctamente'}), 201
    except Exception as e:
        return error_desde_excepcion(e, db, 'inscribir al jugador')


@admin_bp.route('/jugadores/editar/<int:id>', methods=['PUT'])
def editar_jugador(id):
    try:
        jugador = Jugador.query.get_or_404(id)
        datos = validar_jugador(request.get_json(silent=True) or {}, id_actual=id)
        for campo, valor in datos.items():
            setattr(jugador, campo, valor)
        db.session.commit()
        return jsonify({'mensaje': 'Jugador actualizado correctamente'}), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'actualizar al jugador')


@admin_bp.route('/jugadores/eliminar/<int:id>', methods=['DELETE'])
def eliminar_jugador(id):
    try:
        jugador = Jugador.query.get_or_404(id)

        # 1. Eliminamos los pagos asociados si existen
        Pago.query.filter_by(jugador_id=id).delete()

        # 2. Eliminamos el jugador
        db.session.delete(jugador)
        db.session.commit()
        return jsonify({'mensaje': 'Jugador eliminado correctamente'}), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'eliminar al jugador')

# ==========================================
# GESTIÓN DE PAGOS
# ==========================================
@admin_bp.route('/pagos', methods=['GET'])
def listar_pagos():
    try:
        pagos = Pago.query.all()
        resultado = []
        for p in pagos:
            resultado.append({
                'id': p.id,
                'monto': p.monto,
                'fecha_pago': p.fecha_pago.strftime('%Y-%m-%d') if p.fecha_pago else None,
                'concepto': p.mes or 'Mensualidad',
                'estado': normalizar_estado(p.estado),
                'detalle_reporte': p.comprobante_img,
                'metodo_pago': (p.comprobante_img or '').split('; Referencia:')[0].replace('Medio: ', '').strip() or 'No especificado',
                'jugador_id': p.jugador_id,
                'jugador_nombre': p.jugador.nombre if p.jugador else 'Desconocido'
            })
        return jsonify(resultado), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'cargar los pagos')


def validar_pago(data, jugador_id, campo_motivo):
    motivo = texto(data, campo_motivo)
    if not motivo:
        raise ValidationError('El motivo o concepto del pago es obligatorio.', 400, [campo_motivo])
    if len(motivo) > 100:
        raise ValidationError('El motivo del pago no puede superar los 100 caracteres.', 400, [campo_motivo])
    if data.get('monto') in (None, ''):
        raise ValidationError('Falta completar el campo: Monto.', 400, ['monto'])
    monto = a_numero(data.get('monto'), 'Monto', minimo=0.01)
    if not data.get('fecha_pago'):
        raise ValidationError('Falta completar el campo: Fecha de pago.', 400, ['fecha_pago'])
    fecha = a_fecha(data.get('fecha_pago'), 'Fecha de pago')
    if not Jugador.query.get(jugador_id):
        raise ValidationError('El jugador seleccionado no existe.', 404)
    return motivo, monto, fecha


@admin_bp.route('/pagos/nuevo', methods=['POST'])
def registrar_pago():
    try:
        data = request.get_json(silent=True) or {}
        if not data.get('jugador_id'):
            raise ValidationError('Debes seleccionar un jugador.', 400, ['jugador_id'])
        jugador_id = a_entero(data.get('jugador_id'), 'Jugador')
        motivo, monto, fecha = validar_pago(data, jugador_id, 'motivo')
        if not data.get('estado'):
            raise ValidationError('Falta completar el campo: Estado del pago.', 400, ['estado'])

        nuevo_pago = Pago(
            monto=monto,
            fecha_pago=fecha,
            mes=motivo,  # el motivo se guarda en la columna existente 'mes'
            estado=normalizar_estado(data.get('estado')),
            jugador_id=jugador_id
        )
        db.session.add(nuevo_pago)
        db.session.commit()
        return jsonify({'mensaje': 'Pago registrado con éxito'}), 201
    except Exception as e:
        return error_desde_excepcion(e, db, 'registrar el pago')

# ==========================================
# DETALLE Y REGISTRO DE PAGOS POR JUGADOR
# ==========================================
@admin_bp.route('/jugadores/<int:id>/pagos', methods=['GET'])
def obtener_pagos_jugador(id):
    try:
        jugador = Jugador.query.get_or_404(id)
        pagos = Pago.query.filter_by(jugador_id=id).order_by(Pago.id.desc()).all()

        historial = []
        for p in pagos:
            historial.append({
                'id': p.id,
                'mes': p.mes or 'Sin motivo',
                'monto': p.monto,
                'fecha_pago': p.fecha_pago.strftime('%Y-%m-%d') if p.fecha_pago else None,
                'concepto': p.mes or 'Mensualidad',
                'estado': normalizar_estado(p.estado)
            })

        return jsonify({
            'jugador': {'id': jugador.id, 'nombre': jugador.nombre},
            'historial': historial
        }), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'cargar el historial de pagos')


@admin_bp.route('/jugadores/<int:id>/pagos/nuevo', methods=['POST'])
def registrar_pago_jugador(id):
    try:
        data = request.get_json(silent=True) or {}
        motivo, monto, fecha = validar_pago(data, id, 'mes')
        if not data.get('estado'):
            raise ValidationError('Falta completar el campo: Estado del pago.', 400, ['estado'])

        nuevo_pago = Pago(
            monto=monto,
            fecha_pago=fecha,
            mes=motivo,
            estado=normalizar_estado(data.get('estado')),
            jugador_id=id
        )
        db.session.add(nuevo_pago)
        db.session.commit()
        return jsonify({'mensaje': 'Pago registrado con éxito'}), 201
    except Exception as e:
        return error_desde_excepcion(e, db, 'registrar el pago')


@admin_bp.route('/pagos/<int:pago_id>/estado', methods=['PUT'])
def actualizar_estado_pago(pago_id):
    """HU025: cambia el estado de un pago (Pendiente, Pagado o Atrasado)."""
    try:
        pago = Pago.query.get_or_404(pago_id)
        estado = ((request.get_json(silent=True) or {}).get('estado') or '').strip().capitalize()
        if estado not in ESTADOS_PAGO:
            raise ValidationError('Estado inválido. Usa Pendiente, Pagado o Atrasado.')
        pago.estado = estado
        db.session.commit()
        return jsonify({'mensaje': 'Estado actualizado', 'estado': estado}), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'actualizar el estado del pago')


@admin_bp.route('/pagos/<int:pago_id>', methods=['DELETE'])
def eliminar_pago(pago_id):
    try:
        pago = Pago.query.get_or_404(pago_id)
        db.session.delete(pago)
        db.session.commit()
        return jsonify({'mensaje': 'Pago eliminado'}), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'eliminar el pago')

# ==========================================
# AUXILIARES PARA FORMULARIOS
# ==========================================
@admin_bp.route('/acudientes', methods=['GET'])
def listar_acudientes():
    # Obtiene solo usuarios con rol 'acudiente'
    acudientes = Usuario.query.filter_by(rol='acudiente').all()
    resultado = [{'id': a.id, 'nombre_completo': a.nombre_completo} for a in acudientes]
    return jsonify(resultado), 200

# =========================
# CATEGORÍAS
# =========================

def validar_categoria(data, id_actual=None):
    exigir_campos(data, {'nombre': 'Nombre de la categoría', 'profesor_id': 'Entrenador asignado'})
    nombre = texto(data, 'nombre')
    if len(nombre) < 2 or len(nombre) > 50:
        raise ValidationError('El nombre de la categoría debe tener entre 2 y 50 caracteres.')
    profesor_id = a_entero(data.get('profesor_id'), 'Entrenador asignado')
    profesor = Usuario.query.get(profesor_id)
    if not profesor or profesor.rol != 'profesor':
        raise ValidationError('El entrenador seleccionado no existe o no tiene rol de profesor.')
    duplicada = Categoria.query.filter(db.func.lower(Categoria.nombre) == nombre.lower()).first()
    if duplicada and duplicada.id != id_actual:
        raise ValidationError('Ya existe una categoría con ese nombre.', 409, ['nombre'])
    return nombre, profesor_id


@admin_bp.route('/categorias', methods=['GET'])
def listar_categorias():
    try:
        categorias = Categoria.query.all()
        resultado = [{
            'id': c.id,
            'nombre': c.nombre,
            'profesor_id': c.profesor_id,
            'profesor': c.profesor.nombre_completo if c.profesor else None,
            'jugadores': len(c.jugadores)
        } for c in categorias]
        return jsonify(resultado), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'cargar las categorías')


@admin_bp.route('/categorias/nueva', methods=['POST', 'OPTIONS'])
def crear_categoria():
    if request.method == 'OPTIONS':
        return '', 200

    try:
        nombre, profesor_id = validar_categoria(request.get_json(silent=True) or {})
        nueva_cat = Categoria(nombre=nombre, profesor_id=profesor_id)
        db.session.add(nueva_cat)
        db.session.commit()
        return jsonify({'mensaje': 'Categoría creada con éxito', 'id': nueva_cat.id}), 201
    except Exception as e:
        return error_desde_excepcion(e, db, 'crear la categoría')


@admin_bp.route('/categorias/<int:id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def gestionar_categoria(id):
    if request.method == 'OPTIONS':
        return '', 200

    try:
        categoria = Categoria.query.get_or_404(id)

        if request.method == 'GET':
            return jsonify({
                'id': categoria.id,
                'nombre': categoria.nombre,
                'profesor_id': categoria.profesor_id
            }), 200

        if request.method == 'PUT':
            data = request.get_json(silent=True) or {}
            combinado = {
                'nombre': data.get('nombre', categoria.nombre),
                'profesor_id': data.get('profesor_id', categoria.profesor_id)
            }
            nombre, profesor_id = validar_categoria(combinado, id_actual=id)
            categoria.nombre = nombre
            categoria.profesor_id = profesor_id
            db.session.commit()
            return jsonify({'mensaje': 'Categoría actualizada con éxito'}), 200

        # DELETE
        for j in categoria.jugadores:
            j.categoria_id = None
        if categoria.eventos:
            raise ValidationError(
                f'No se puede eliminar: la categoría tiene {len(categoria.eventos)} entrenamiento(s) o partido(s) programado(s).', 409)
        db.session.delete(categoria)
        db.session.commit()
        return jsonify({'mensaje': 'Categoría eliminada con éxito'}), 200
    except Exception as e:
        return error_desde_excepcion(e, db, 'procesar la categoría')

# ==========================================
# AUXILIAR PARA SELECCIÓN DE PROFESORES
# ==========================================
@admin_bp.route('/profesores', methods=['GET'])
def listar_profesores():
    # Consulta a los usuarios cuya función/rol sea 'profesor'
    profesores = Usuario.query.filter_by(rol='profesor').all()
    resultado = [{'id': p.id, 'nombre_completo': p.nombre_completo} for p in profesores]
    return jsonify(resultado), 200
