import os, time
from app import create_app
from db import db
from models import Student, Company
from tasks import export_applications_csv, celery

app = create_app()
EXPORT_DIR = os.path.join(app.config.get('UPLOAD_FOLDER','uploads'),'exports')
if not os.path.exists(EXPORT_DIR): os.makedirs(EXPORT_DIR, exist_ok=True)

with app.app_context():
    # pick one student and one company
    s = Student.query.first()
    c = Company.query.first()
    student_user_id = None
    company_id = None
    if s:
        student_user_id = s.user_id
    if c:
        company_id = c.id
    print('Using student user_id:', student_user_id, 'company_id:', company_id)

    tasks = []
    if student_user_id:
        t = export_applications_csv.apply_async(args=[student_user_id, 'student'])
        print('Queued student task:', t.id)
        tasks.append(('student', t))
    if company_id:
        t = export_applications_csv.apply_async(args=[company_id, 'company'])
        print('Queued company task:', t.id)
        tasks.append(('company', t))
    # admin full export
    t = export_applications_csv.apply_async(args=[None, 'admin'])
    print('Queued admin task:', t.id)
    tasks.append(('admin', t))

    # poll
    for role, async_res in tasks:
        print(f'Polling {role} task {async_res.id}...')
        waited = 0
        while waited < 60:
            res = celery.AsyncResult(async_res.id)
            state = res.state
            info = res.info
            print(' ', role, 'state=', state)
            if state == 'SUCCESS' or state == 'FAILURE':
                break
            time.sleep(1)
            waited += 1
        print('Final state for', role, res.state)
        # find file
        found = None
        for f in os.listdir(EXPORT_DIR):
            if async_res.id in f:
                found = os.path.join(EXPORT_DIR, f)
                break
        if found and os.path.exists(found):
            size = os.path.getsize(found)
            print(' File found:', found, 'size=', size)
            with open(found, 'r', encoding='utf-8', errors='ignore') as fp:
                lines = fp.read().splitlines()
                print('  First 10 lines:')
                for i, ln in enumerate(lines[:10]):
                    print('   ', i+1, ln)
        else:
            print(' No file generated for', role)

print('Done')
