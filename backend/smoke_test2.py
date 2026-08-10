from tasks import export_applications_csv, send_interview_reminders, generate_monthly_placement_report, app, celery
from models import Student, Company
import time

with app.app_context():
    student = Student.query.first()
    comp = Company.query.first()
    print('student id', student.user_id if student else None)
    # export
    if student:
        ar = export_applications_csv.apply_async(args=[student.user_id, 'student'])
        print('export task id', ar.id)
        for _ in range(30):
            st = celery.AsyncResult(ar.id)
            print('state', st.state)
            if st.state in ('SUCCESS','FAILURE'):
                print('final info', st.info)
                break
            time.sleep(1)
    # reminders
    ar2 = send_interview_reminders.apply_async()
    print('reminders id', ar2.id)
    for _ in range(10):
        st = celery.AsyncResult(ar2.id)
        print('rem state', st.state)
        if st.state in ('SUCCESS','FAILURE'):
            print('rem info', st.info)
            break
        time.sleep(1)
    # report
    ar3 = generate_monthly_placement_report.apply_async()
    print('report id', ar3.id)
    for _ in range(10):
        st = celery.AsyncResult(ar3.id)
        print('rep state', st.state)
        if st.state in ('SUCCESS','FAILURE'):
            print('rep info', st.info)
            break
        time.sleep(1)
print('done')
