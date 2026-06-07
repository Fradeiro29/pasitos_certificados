from flask import Blueprint, render_template, request

from app import crypto
from app.database import get_db

verificar_bp = Blueprint('verificar', __name__)


@verificar_bp.route('/verificar')
def verificar():
    folio = request.args.get('folio', '').strip()

    if not folio:
        return render_template('verificar.html', estado='sin_folio', folio='', cert=None)

    conn = get_db()
    cert = conn.execute(
        '''SELECT c.*, p.nombre AS nombre_persona, cu.nombre AS nombre_curso
           FROM certificados c
           JOIN personas p ON c.curp = p.curp
           JOIN cursos cu ON c.id_curso = cu.id
           WHERE c.folio = ?''',
        (folio,),
    ).fetchone()
    conn.close()

    if not cert:
        return render_template('verificar.html', estado='invalido', folio=folio, cert=None)

    hash_recalculado = crypto.generate_hash(cert['curp'], cert['id_curso'], folio)
    firma_valida = crypto.verify_signature(hash_recalculado, cert['firma_ecdsa'])

    estado = 'valido' if firma_valida else 'alterado'
    return render_template('verificar.html', estado=estado, folio=folio, cert=cert)
