from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.auth import login as auth_login

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    if 'username' in session:
        return redirect(url_for('personas.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if auth_login(username, password):
            session['username'] = username
            return redirect(url_for('personas.dashboard'))

        flash('Usuario o contraseña incorrectos', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login_page'))
