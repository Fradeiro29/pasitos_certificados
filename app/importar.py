import os
from datetime import datetime, date

import openpyxl

from app.database import get_db

EXCEL_PATH = '/app/Pasitos_Registro_Cursos.xlsx'


def _str(val, default=''):
    if val is None:
        return default
    if isinstance(val, (datetime, date)):
        return val.strftime('%d/%m/%Y')
    return str(val).strip()


def _build_col_map(worksheet, header_row):
    col_map = {}
    for i, cell in enumerate(worksheet[header_row]):
        if cell.value is not None:
            col_map[str(cell.value).strip()] = i
    return col_map


def _get(row, col_map, col_name, default=''):
    idx = col_map.get(col_name)
    if idx is None or idx >= len(row):
        return default
    return _str(row[idx], default)


def importar_desde_excel(filepath=EXCEL_PATH):
    resultado = {'personas': 0, 'cursos': 0, 'errores': []}

    if not os.path.exists(filepath):
        resultado['errores'].append(f'Archivo no encontrado: {filepath}')
        return resultado

    try:
        wb = openpyxl.load_workbook(filepath, data_only=True)
    except Exception as e:
        resultado['errores'].append(f'Error abriendo archivo: {e}')
        return resultado

    conn = get_db()

    # --- Catálogo de Cursos: encabezados fila 3, datos desde fila 4 ---
    sheet_cursos = 'Catálogo de Cursos'
    if sheet_cursos in wb.sheetnames:
        ws = wb[sheet_cursos]
        col_map = _build_col_map(ws, 3)
        for row in ws.iter_rows(min_row=4, values_only=True):
            if not row or row[0] is None:
                continue
            try:
                id_curso = _get(row, col_map, 'ID Curso')
                nombre = _get(row, col_map, 'Nombre del Curso')
                if not id_curso or not nombre:
                    continue
                tipo = _get(row, col_map, 'Tipo / Formato')
                duracion_raw = row[col_map['Duración (horas)']] if 'Duración (horas)' in col_map else None
                duracion = int(duracion_raw) if duracion_raw is not None else None
                modalidad = _get(row, col_map, 'Modalidad')
                descripcion = _get(row, col_map, 'Descripción')
                estado = _get(row, col_map, 'Estado') or 'Activo'

                conn.execute(
                    '''INSERT OR IGNORE INTO cursos
                       (id, nombre, tipo, duracion_horas, modalidad, descripcion, estado)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (id_curso, nombre, tipo, duracion, modalidad, descripcion, estado),
                )
                resultado['cursos'] += 1
            except Exception as e:
                resultado['errores'].append(f'Curso: {e}')
    else:
        resultado['errores'].append(f'Hoja "{sheet_cursos}" no encontrada')

    # --- Registro de Inscripciones: encabezados fila 4, datos desde fila 5 ---
    sheet_reg = 'Registro de Inscripciones'
    if sheet_reg in wb.sheetnames:
        ws = wb[sheet_reg]
        col_map = _build_col_map(ws, 4)
        for row in ws.iter_rows(min_row=5, values_only=True):
            if not row or row[0] is None:
                continue
            try:
                nombre = _get(row, col_map, 'Nombre Completo')
                curp = _get(row, col_map, 'CURP').upper()
                if not nombre or not curp:
                    continue
                if len(curp) != 18:
                    resultado['errores'].append(f'CURP inválida ({len(curp)} chars): {curp}')
                    continue
                fecha_nac = _get(row, col_map, 'Fecha de Nacimiento')
                grado = _get(row, col_map, 'Último Grado de Estudio')
                correo = _get(row, col_map, 'Correo Electrónico')
                institucion = _get(row, col_map, 'Institución / Guardería')
                cargo = _get(row, col_map, 'Cargo o Puesto')

                conn.execute(
                    '''INSERT OR IGNORE INTO personas
                       (nombre, curp, fecha_nacimiento, grado_estudio, correo, institucion, cargo)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (nombre, curp, fecha_nac, grado, correo, institucion, cargo),
                )
                resultado['personas'] += 1
            except Exception as e:
                resultado['errores'].append(f'Persona: {e}')
    else:
        resultado['errores'].append(f'Hoja "{sheet_reg}" no encontrada')

    conn.commit()
    conn.close()
    return resultado
