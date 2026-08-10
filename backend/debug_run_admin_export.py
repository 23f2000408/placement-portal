import os
from app import create_app
from db import db
from models import Application, User, Student, Company, PlacementDrive

app = create_app()
EXPORT_DIR = os.path.join(app.config.get('UPLOAD_FOLDER','uploads'),'exports')
if not os.path.exists(EXPORT_DIR): os.makedirs(EXPORT_DIR, exist_ok=True)
path = os.path.join(EXPORT_DIR, 'debug_admin_export.csv')

with app.app_context():
    try:
        with open(path,'w',newline='',encoding='utf-8') as csvfile:
            import csv
            writer = csv.writer(csvfile)
            writer.writerow(['Application ID','Student Email','Student Name','Company','Drive Title','Status','Applied At'])
            apps = db.session.query(Application.id,
                                    User.email.label('student_email'),
                                    Student.name.label('student_name'),
                                    Company.name.label('company_name'),
                                    PlacementDrive.title.label('drive_title'),
                                    Application.status,
                                    Application.applied_at).join(Student, Application.student_id == Student.id).join(User, Student.user_id == User.id).join(PlacementDrive, Application.drive_id == PlacementDrive.id).outerjoin(Company, PlacementDrive.company_id == Company.id).all()
            print('Rows fetched:', len(apps))
            for app_row in apps:
                writer.writerow(list(app_row))
        print('Wrote', path)
    except Exception as e:
        import traceback
        print('Export failed:', e)
        traceback.print_exc()
