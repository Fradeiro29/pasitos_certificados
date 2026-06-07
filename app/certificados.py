import json
import os
from datetime import datetime
from io import BytesIO

import qrcode
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app import crypto
from app.database import CERTS_DIR, get_db

TEMPLATE_PATH = '/app/plantilla_certificado.png'
COORDS_PATH = '/app/coordenadas.json'
IMG_WIDTH = 1920
IMG_HEIGHT = 1280


def _load_coords():
    with open(COORDS_PATH, encoding='utf-8') as f:
        return json.load(f)


def _next_seq(conn, year):
    row = conn.execute(
        "SELECT COALESCE(MAX(CAST(SUBSTR(folio, 10) AS INTEGER)), 0) AS max_seq "
        "FROM certificados WHERE folio LIKE ?",
        (f'VER-{year}-%',),
    ).fetchone()
    return row['max_seq'] + 1


def _make_qr_buffer(url):
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def _generar_pdf(persona, curso, cert_data, folio):
    coords = _load_coords()
    base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
    qr_url = f"{base_url}/verificar?folio={folio}"

    pdf_path = os.path.join(CERTS_DIR, f'{folio}.pdf')
    c = canvas.Canvas(pdf_path, pagesize=(IMG_WIDTH, IMG_HEIGHT))

    # Fondo
    c.drawImage(TEMPLATE_PATH, 0, 0, width=IMG_WIDTH, height=IMG_HEIGHT)

    def y_rl(y_json, font_size=0):
        # Convierte Y imagen (origen arriba) a Y reportlab (origen abajo)
        # font_size ajusta para que la línea base quede en el punto indicado
        return IMG_HEIGHT - y_json - font_size

    fields = {
        'nombre':         (str(persona['nombre']),            'Helvetica-Bold', 48),
        'curp':           (str(persona['curp']),              'Helvetica',      24),
        'curso':          (str(curso['nombre']),              'Helvetica-Bold', 40),
        'no_certificado': (str(cert_data['no_certificado']), 'Helvetica-Bold', 28),
        'fecha_emision':  (str(cert_data['fecha_emision']),  'Helvetica',      22),
        'folio':          (str(folio),                        'Helvetica-Bold', 32),
    }

    for field, (text, font, size) in fields.items():
        if field not in coords:
            continue
        x = coords[field]['x']
        y = y_rl(coords[field]['y'], size)
        c.setFont(font, size)
        c.drawString(x, y, text)

    # QR
    if 'qr' in coords:
        qr_size = 200
        qr_x = coords['qr']['x']
        qr_y = y_rl(coords['qr']['y'] + qr_size)  # top-left JSON → bottom-left RL
        qr_buf = _make_qr_buffer(qr_url)
        c.drawImage(ImageReader(qr_buf), qr_x, qr_y, width=qr_size, height=qr_size)

    c.save()
    return pdf_path


def regenerar_pdf(folio):
    conn = get_db()
    cert = conn.execute('SELECT * FROM certificados WHERE folio = ?', (folio,)).fetchone()
    if not cert:
        conn.close()
        raise ValueError(f'Folio {folio} no encontrado')

    persona = conn.execute('SELECT * FROM personas WHERE curp = ?', (cert['curp'],)).fetchone()
    curso = conn.execute('SELECT * FROM cursos WHERE id = ?', (cert['id_curso'],)).fetchone()

    cert_data = {
        'no_certificado': cert['no_certificado'],
        'fecha_emision':  cert['fecha_emision'],
    }
    pdf_path = _generar_pdf(persona, curso, cert_data, folio)
    conn.execute('UPDATE certificados SET pdf_path = ? WHERE folio = ?', (pdf_path, folio))
    conn.commit()
    conn.close()
    return pdf_path


def generar_certificado(curp, id_curso, calificacion, fecha_inicio, fecha_termino):
    conn = get_db()

    persona = conn.execute('SELECT * FROM personas WHERE curp = ?', (curp,)).fetchone()
    if not persona:
        conn.close()
        raise ValueError(f'Persona con CURP {curp} no encontrada')

    curso = conn.execute('SELECT * FROM cursos WHERE id = ?', (id_curso,)).fetchone()
    if not curso:
        conn.close()
        raise ValueError(f'Curso {id_curso} no encontrado')

    year = datetime.now().year
    seq = _next_seq(conn, year)
    folio = f'VER-{year}-{seq:04d}'
    no_certificado = f'PAC-{year}-{seq:04d}'
    fecha_emision = datetime.now().strftime('%d/%m/%Y')

    hash_val = crypto.generate_hash(curp, id_curso, folio)
    firma = crypto.sign_data(hash_val)
    resultado = 'Aprobado' if float(calificacion) >= 6.0 else 'No Aprobado'

    conn.execute(
        '''INSERT INTO certificados
           (folio, no_certificado, curp, id_curso, calificacion, resultado,
            fecha_inicio, fecha_termino, fecha_emision, hash_sha256, firma_ecdsa)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (folio, no_certificado, curp, id_curso, float(calificacion), resultado,
         fecha_inicio, fecha_termino, fecha_emision, hash_val, firma),
    )
    conn.commit()

    cert_data = {'no_certificado': no_certificado, 'fecha_emision': fecha_emision}
    try:
        pdf_path = _generar_pdf(persona, curso, cert_data, folio)
        conn.execute('UPDATE certificados SET pdf_path = ? WHERE folio = ?', (pdf_path, folio))
        conn.commit()
    except Exception as e:
        print(f'[CERT] Error generando PDF para {folio}: {e}')

    conn.close()
    return folio
