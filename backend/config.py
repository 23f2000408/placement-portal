import os
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'placement.db')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
