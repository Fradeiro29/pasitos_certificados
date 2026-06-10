import os
import re
import tempfile

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.auth import login_required
from app.database import get_db
from app.importar import importar_desde_excel, validar_formato

personas_bp = Blueprint('personas', __name__)

_CURP_RE = re.compile(r'^[A-Z0-9]{18}$')


@personas_bp.route('/')
@personas_bp.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    total_personas = conn.execute('SELECT COUNT(*) AS c FROM personas').fetchone()['c']
    total_certs = conn.execute('SELECT COUNT(*) AS c FROM certificados').fetchone()['c']
    ultimo = conn.execute(
        '''SELECT c.folio, c.fecha_emision, p.nombre
           FROM certificados c
           JOIN personas p ON c.curp = p.curp
           ORDER BY c.created_at DESC LIMIT 1'''
    ).fetchone()
    conn.close()
    return render_template('dashboard.html',
                           total_personas=total_personas,
                           total_certs=total_certs,
                           ultimo=ultimo)


@personas_bp.route('/personas')
@login_required
def personas():
    conn = get_db()
    lista = conn.execute('SELECT * FROM personas ORDER BY nombre').fetchall()
    conn.close()
    return render_template('personas.html', personas=lista, importacion=None)


@personas_bp.route('/personas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_persona():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        curp = request.form.get('curp', '').strip().upper()
        fecha_nac = request.form.get('fecha_nacimiento', '').strip()
        grado = request.form.get('grado_estudio', '').strip()
        correo = request.form.get('correo', '').strip()
        institucion = request.form.get('institucion', '').strip()
        cargo = request.form.get('cargo', '').strip()

        if not nombre or not curp:
            flash('Nombre y CURP son obligatorios', 'error')
        elif not _CURP_RE.match(curp):
            flash('La CURP debe tener exactamente 18 caracteres alfanuméricos (A-Z, 0-9)', 'error')
        else:
            try:
                conn = get_db()
                conn.execute(
                    '''INSERT INTO personas
                       (nombre, curp, fecha_nacimiento, grado_estudio, correo, institucion, cargo)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (nombre, curp, fecha_nac, grado, correo, institucion, cargo),
                )
                conn.commit()
                conn.close()
                flash(f'Persona registrada correctamente: {nombre}', 'success')
                return redirect(url_for('personas.personas'))
            except Exception:
                flash('Error: la CURP ya existe en el sistema', 'error')

    return render_template('nueva_persona.html')


@personas_bp.route('/personas/importar', methods=['POST'])
@login_required
def importar_personas():
    archivo = request.files.get('archivo_excel')

    if not archivo or archivo.filename == '':
        flash('No seleccionaste ningún archivo.', 'error')
        return redirect(url_for('personas.personas'))

    ext = os.path.splitext(archivo.filename)[1].lower()
    if ext not in {'.xlsx', '.xls', '.csv'}:
        flash('Archivo no válido: solo se aceptan .xlsx, .xls y .csv con el formato Pasitos.', 'error')
        return redirect(url_for('personas.personas'))

    # Guardar en archivo temporal conservando la extensión original
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext)
    try:
        os.close(tmp_fd)
        archivo.save(tmp_path)

        errores_fmt = validar_formato(tmp_path)
        if errores_fmt:
            flash('Archivo no válido: ' + ' · '.join(errores_fmt), 'error')
            return redirect(url_for('personas.personas'))

        resultado = importar_desde_excel(tmp_path)
    finally:
        os.unlink(tmp_path)

    conn = get_db()
    lista = conn.execute('SELECT * FROM personas ORDER BY nombre').fetchall()
    conn.close()
    return render_template('personas.html', personas=lista, importacion=resultado)
