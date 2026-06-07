import os

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from app.auth import login_required
from app.certificados import generar_certificado as gen_cert, regenerar_pdf
from app.database import CERTS_DIR, get_db

certificados_bp = Blueprint('certificados', __name__)


@certificados_bp.route('/certificados')
@login_required
def certificados():
    conn = get_db()
    lista = conn.execute(
        '''SELECT c.*, p.nombre AS nombre_persona, cu.nombre AS nombre_curso
           FROM certificados c
           JOIN personas p ON c.curp = p.curp
           JOIN cursos cu ON c.id_curso = cu.id
           ORDER BY c.created_at DESC'''
    ).fetchall()
    personas = conn.execute('SELECT curp, nombre FROM personas ORDER BY nombre').fetchall()
    cursos = conn.execute("SELECT id, nombre FROM cursos WHERE estado = 'Activo'").fetchall()
    conn.close()
    return render_template('certificados.html',
                           certificados=lista,
                           personas=personas,
                           cursos=cursos)


@certificados_bp.route('/certificados/generar', methods=['POST'])
@login_required
def generar():
    curp = request.form.get('curp', '').strip()
    id_curso = request.form.get('id_curso', '').strip()
    calificacion = request.form.get('calificacion', '').strip()
    fecha_inicio = request.form.get('fecha_inicio', '').strip()
    fecha_termino = request.form.get('fecha_termino', '').strip()

    if not curp or not id_curso or not calificacion:
        flash('CURP, curso y calificación son obligatorios', 'error')
        return redirect(url_for('certificados.certificados'))

    try:
        cal = float(calificacion)
        if not (0.0 <= cal <= 10.0):
            raise ValueError()
    except ValueError:
        flash('La calificación debe ser un número entre 0 y 10', 'error')
        return redirect(url_for('certificados.certificados'))

    try:
        folio = gen_cert(curp, id_curso, cal, fecha_inicio, fecha_termino)
        flash(f'Certificado emitido exitosamente: {folio}', 'success')
    except Exception as e:
        flash(f'Error al generar certificado: {e}', 'error')

    return redirect(url_for('certificados.certificados'))


@certificados_bp.route('/certificados/descargar/<folio>')
@login_required
def descargar(folio):
    conn = get_db()
    cert = conn.execute(
        'SELECT pdf_path FROM certificados WHERE folio = ?', (folio,)
    ).fetchone()
    conn.close()

    if not cert:
        flash('Certificado no encontrado', 'error')
        return redirect(url_for('certificados.certificados'))

    pdf_path = cert['pdf_path']

    # Si el archivo no existe en disco, regenerarlo automáticamente
    if not pdf_path or not os.path.exists(pdf_path):
        try:
            pdf_path = regenerar_pdf(folio)
        except Exception as e:
            flash(f'No se pudo regenerar el PDF: {e}', 'error')
            return redirect(url_for('certificados.certificados'))

    # Verificar que la ruta está dentro del directorio de certificados
    if not os.path.realpath(pdf_path).startswith(os.path.realpath(CERTS_DIR)):
        flash('Ruta de archivo inválida', 'error')
        return redirect(url_for('certificados.certificados'))

    return send_file(pdf_path, as_attachment=True, download_name=f'{folio}.pdf')
