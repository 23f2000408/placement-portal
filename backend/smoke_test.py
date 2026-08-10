import time
from tasks import export_applications_csv, send_interview_reminders, generate_monthly_placement_report, app
from models import Student, Company

print('Running smoke tests...')
with app.app_context():
    # find a student
    student = Student.query.first()
    company = Company.query.first()
    print('Found student:', bool(student), 'Found company:', bool(company))
    if student:
        user_id = student.user_id
        print('Student user_id:', user_id)
        ar = export_applications_csv.apply_async(args=[user_id, 'student'])
        print('Export task id:', ar.id)
        try:
            res = ar.get(timeout=30)
            print('Export result:', res)
        except Exception as e:
            print('Export task error or timeout:', e)
    else:
        print('No student to test export')

    # run reminders
    ar2 = send_interview_reminders.apply_async()
    print('Reminders task id:', ar2.id)
    try:
        res2 = ar2.get(timeout=30)
        print('Reminders result:', res2)
    except Exception as e:
        print('Reminders task error or timeout:', e)

    # run monthly report
    ar3 = generate_monthly_placement_report.apply_async()
    print('Monthly report task id:', ar3.id)
    try:
        res3 = ar3.get(timeout=30)
        print('Monthly report result:', res3)
    except Exception as e:
        print('Monthly report task error or timeout:', e)

print('Done')
