from flask import Flask, render_template
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from config import DATABASE_URI, SECRET_KEY, JWT_SECRET_KEY, UPLOAD_FOLDER, MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USE_SSL, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER
from db import db

mail = Mail()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='../frontend/static')
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Mail config
    app.config['MAIL_SERVER'] = MAIL_SERVER
    app.config['MAIL_PORT'] = MAIL_PORT
    app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
    app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
    app.config['MAIL_USERNAME'] = MAIL_USERNAME
    app.config['MAIL_PASSWORD'] = MAIL_PASSWORD
    app.config['MAIL_DEFAULT_SENDER'] = MAIL_DEFAULT_SENDER

    db.init_app(app)
    jwt = JWTManager(app)
    mail.init_app(app)

    # Register API blueprints
    try:
        from api.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
    except Exception:
        pass

    try:
        from api.drives import drives_bp
        app.register_blueprint(drives_bp, url_prefix='/api/drives')
    except Exception:
        pass

    try:
        from api.status import status_bp
        app.register_blueprint(status_bp, url_prefix='/api')
    except Exception:
        pass

    try:
        from api.admin import admin_bp
        app.register_blueprint(admin_bp, url_prefix='/api/admin')
    except Exception:
        pass

    try:
        from api.student import student_bp
        app.register_blueprint(student_bp, url_prefix='/api/student')
    except Exception:
        pass

    @app.route('/')
    def index():
        # Entry point served via Jinja2 (loads the Vue SPA from CDN/static)
        return render_template('index.html')

    @app.route('/reset-password')
    def reset_password_page():
        # Simple reset page that reads token from query string and posts to API
        return render_template('reset_password.html')

    return app

# Expose a simple runnable app for local dev
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
