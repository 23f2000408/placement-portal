from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from config import DATABASE_URI, SECRET_KEY, JWT_SECRET_KEY, UPLOAD_FOLDER

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='../frontend/static')
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    db.init_app(app)
    jwt = JWTManager(app)

    # Register API blueprints
    try:
        from api.auth import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/api/auth')
    except Exception:
        pass

    @app.route('/')
    def index():
        # Entry point served via Jinja2 (loads the Vue SPA from CDN/static)
        return render_template('index.html')

    return app

# Expose a simple runnable app for local dev
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
