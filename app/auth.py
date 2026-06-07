from functools import wraps

import bcrypt
from flask import session, redirect, url_for

from app.database import get_db


def login(username: str, password: str) -> bool:
    conn = get_db()
    user = conn.execute(
        'SELECT password_hash FROM usuarios WHERE username = ?', (username,)
    ).fetchone()
    conn.close()

    if user is None:
        return False

    return bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8'))


def check_session() -> bool:
    return 'username' in session


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not check_session():
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated
