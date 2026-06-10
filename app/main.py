import os
import sys

# Ensure project root is in path when running as: python app/main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from app.database import init_db
from app.crypto import init_keys
from app.routes.auth_routes import auth_bp
from app.routes.personas_routes import personas_bp
from app.routes.certificados_routes import certificados_bp
from app.routes.verificar_routes import verificar_bp

template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-change-me')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB máximo por upload

app.register_blueprint(auth_bp)
app.register_blueprint(personas_bp)
app.register_blueprint(certificados_bp)
app.register_blueprint(verificar_bp)

if __name__ == '__main__':
    init_db()
    init_keys('/app/keys')

    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=5000, debug=debug)
