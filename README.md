# Pasitos Certificados

Sistema de certificación digital seguro para **Pasitos Education & Health A.C.**

Genera certificados PDF firmados con ECDSA (curva P-256) y los verifica mediante un QR público.

---

## Requisitos

- [Docker](https://www.docker.com/get-started) y Docker Compose

---

## Instalación y arranque

```bash
# 1. Copia el archivo de entorno
cp .env.example .env

# 2. (Opcional) Edita .env para cambiar la clave secreta y la URL base
#    FLASK_SECRET_KEY=una_clave_muy_larga_y_aleatoria
#    BASE_URL=http://tu-dominio.com   ← importante para que el QR apunte al servidor correcto

# 3. Construye y arranca
docker compose up --build
```

Abre **http://localhost:5000** en el navegador.

**Credenciales por defecto:** `admin` / `pasitos2025`

> Cambia la contraseña en producción modificando el hash en la tabla `usuarios` de la base de datos.

---

## Flujo de uso

1. **Importar datos** → `/personas/importar`  
   Carga personas y cursos desde `Pasitos Registro Cursos.xlsx` automáticamente.

2. **Registrar personas** → `/personas/nueva`  
   Agrega participantes manualmente (requiere CURP de 18 caracteres).

3. **Emitir certificado** → `/certificados`  
   Selecciona persona + curso + calificación y genera el PDF firmado.

4. **Descargar PDF** → botón "PDF" en la tabla de certificados.  
   El PDF incluye los datos sobre la plantilla y un código QR de verificación.

5. **Verificar** → el empleador escanea el QR del PDF  
   O visita directamente `/verificar?folio=VER-2026-0001`.

---

## Cómo funciona la verificación

Cada certificado emitido se protege con **firma digital ECDSA (P-256)**:

```
hash = SHA256(CURP | id_curso | folio)
firma = ECDSA_sign(hash, clave_privada)
```

Al verificar:

1. Se recalcula el hash con los datos almacenados en la base de datos.
2. Se verifica la firma con la clave pública.
3. Si coinciden → **VÁLIDO** ✅  
   Si los datos fueron alterados → **ALTERADO** ⚠️  
   Si el folio no existe → **NO ENCONTRADO** ❌

Las llaves se generan automáticamente en `keys/` al primer arranque y **nunca deben incluirse en el repositorio** (están en `.gitignore`).

---

## Estructura del proyecto

```
pasitos-certificados/
├── app/
│   ├── main.py          ← entry point Flask
│   ├── crypto.py        ← motor ECDSA (sign / verify / hash)
│   ├── auth.py          ← login, sesiones, bcrypt
│   ├── database.py      ← SQLite, esquema, init
│   ├── certificados.py  ← generación PDF + QR
│   ├── importar.py      ← importación desde Excel
│   ├── routes/          ← blueprints Flask
│   └── templates/       ← HTML (Jinja2)
├── data/
│   ├── pasitos.db       ← base de datos SQLite (generada automáticamente)
│   └── certificados/    ← PDFs generados
├── keys/
│   ├── private_key.pem  ← generada al iniciar (NUNCA en git)
│   └── public_key.pem
├── plantilla_certificado.png
├── coordenadas.json
├── Pasitos Registro Cursos.xlsx
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|---|---|---|
| `FLASK_SECRET_KEY` | Clave para firmar sesiones Flask | cadena larga y aleatoria |
| `FLASK_ENV` | `development` activa modo debug | `production` |
| `BASE_URL` | URL base del servidor (para QR) | `https://certificados.pasitos.mx` |

---

## Persistencia de datos

Los volúmenes de Docker montan:

- `./data` → base de datos SQLite y PDFs generados
- `./keys` → par de llaves ECDSA

Estos directorios **persisten fuera del contenedor**, por lo que los datos no se pierden al hacer `docker compose down`.

---

## Producción

Para desplegar en un servidor:

1. Cambia `BASE_URL` en `.env` al dominio real.
2. Usa un reverse proxy (nginx/Caddy) con HTTPS frente al puerto 5000.
3. Genera una `FLASK_SECRET_KEY` robusta: `python -c "import secrets; print(secrets.token_hex(32))"`.
4. Cambia `FLASK_ENV=production` en `.env`.
