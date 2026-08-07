
from werkzeug.security import generate_password_hash
from app import create_app, db
from models import User

ADMIN_EMAIL = 'admin@placement.local'
ADMIN_PASSWORD = 'adminpass'


def init_db():
    app = create_app()
    with app.app_context():
        db.create_all()
        existing = User.query.filter_by(email=ADMIN_EMAIL).first()
        if existing:
            print('Admin already exists:', ADMIN_EMAIL)
            return
        admin = User(email=ADMIN_EMAIL, password_hash=generate_password_hash(ADMIN_PASSWORD), role='admin', is_active=True)
        db.session.add(admin)
        db.session.commit()
        print('Admin user created:', ADMIN_EMAIL)


if __name__ == '__main__':
    init_db()
