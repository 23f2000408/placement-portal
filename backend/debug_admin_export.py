from app import create_app
from db import db
from models import Application, User, Student, Company, PlacementDrive

app = create_app()
with app.app_context():
    print('Applications:', Application.query.count())
    print('Students:', Student.query.count())
    print('Users:', User.query.count())
    print('Companies:', Company.query.count())
    print('Drives:', PlacementDrive.query.count())
