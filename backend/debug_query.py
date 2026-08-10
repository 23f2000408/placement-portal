from app import create_app
from db import db
from models import Application, PlacementDrive, Company, Student, User

app = create_app()
with app.app_context():
    student = Student.query.first()
    print('student:', student)
    if student:
        apps = Application.query.filter_by(student_id=student.id).join(PlacementDrive, Application.drive_id == PlacementDrive.id).outerjoin(Company, PlacementDrive.company_id == Company.id).add_columns(Application.id, Company.name, PlacementDrive.title, Application.status, Application.applied_at).all()
        print('len apps:', len(apps))
        for idx,row in enumerate(apps[:5]):
            print(idx, 'type:', type(row), 'len', len(row))
            print(row)
    comp = Company.query.first()
    print('company:', comp)
    if comp:
        apps2 = Application.query.join(PlacementDrive, Application.drive_id == PlacementDrive.id).filter(PlacementDrive.company_id == comp.id).join(Student, Application.student_id == Student.id).join(User, Student.user_id == User.id).add_columns(Application.id, User.email, PlacementDrive.title, Application.status, Application.applied_at).all()
        print('len apps2:', len(apps2))
        for idx,row in enumerate(apps2[:5]):
            print(idx, 'type:', type(row), 'len', len(row))
            print(row)
