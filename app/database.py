import os
import sqlite3

import bcrypt

DB_PATH = '/app/data/pasitos.db'
CERTS_DIR = '/app/data/certificados'


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(CERTS_DIR, exist_ok=True)

    conn = get_db()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cursos (
            id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            tipo TEXT,
            duracion_horas INTEGER,
            modalidad TEXT,
            descripcion TEXT,
            estado TEXT DEFAULT 'Activo'
        );

        CREATE TABLE IF NOT EXISTS personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            curp TEXT UNIQUE NOT NULL,
            fecha_nacimiento TEXT,
            grado_estudio TEXT,
            correo TEXT,
            institucion TEXT,
            cargo TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS certificados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folio TEXT UNIQUE NOT NULL,
            no_certificado TEXT UNIQUE NOT NULL,
            curp TEXT NOT NULL,
            id_curso TEXT NOT NULL,
            calificacion REAL,
            resultado TEXT,
            fecha_inicio TEXT,
            fecha_termino TEXT,
            fecha_emision TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL,
            firma_ecdsa TEXT NOT NULL,
            pdf_path TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (curp) REFERENCES personas(curp),
            FOREIGN KEY (id_curso) REFERENCES cursos(id)
        );
    ''')

    row = conn.execute('SELECT COUNT(*) as c FROM usuarios').fetchone()
    if row['c'] == 0:
        pw_hash = bcrypt.hashpw(b'pasitos2025', bcrypt.gensalt(rounds=12))
        conn.execute(
            'INSERT INTO usuarios (username, password_hash) VALUES (?, ?)',
            ('admin', pw_hash.decode()),
        )

    conn.commit()
    conn.close()
