import os
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'placement.db')
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key')

# Mail (use MailHog locally: SMTP on localhost:1025, Web UI http://localhost:8025)
MAIL_SERVER = os.environ.get('MAIL_SERVER', 'localhost')
MAIL_PORT = int(os.environ.get('MAIL_PORT', 1025))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'false').lower() in ('1','true')
MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ('1','true')
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@placement.local')

UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
