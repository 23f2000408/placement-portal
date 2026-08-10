from tasks import export_applications_csv, send_interview_reminders, generate_monthly_placement_report, app
from models import Student

print('Direct run tests')
with app.app_context():
    student = Student.query.first()
    if student:
        try:
            print('Calling export.__wrapped__ directly')
            # for bound tasks, __wrapped__ is the original function
            res = export_applications_csv.__wrapped__(None, student.user_id, 'student')
            print('export direct res:', res)
        except Exception as e:
            import traceback
            traceback.print_exc()
    try:
        print('Calling reminders.__wrapped__ directly')
        res2 = send_interview_reminders.__wrapped__()
        print('reminders direct res:', res2)
    except Exception:
        import traceback
        traceback.print_exc()
    try:
        print('Calling report.__wrapped__ directly')
        res3 = generate_monthly_placement_report.__wrapped__()
        print('report direct res:', res3)
    except Exception:
        import traceback
        traceback.print_exc()
