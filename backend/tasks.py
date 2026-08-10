import os
import csv
import io
import datetime
from flask import render_template_string, current_app
from flask_mail import Message
from sqlalchemy import func

from app import create_app, mail
from db import db
from models import Application, Interview, User, Company, Placement, PlacementDrive, Student
from celery_app import make_celery

app = create_app()
celery = make_celery(app)

EXPORT_DIR = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'exports')
if not os.path.exists(EXPORT_DIR):
    os.makedirs(EXPORT_DIR, exist_ok=True)


@celery.task(bind=True)
def export_applications_csv(self, user_id, user_role):
    """Export applications/placements for a user (student) or company asynchronously.
    Returns path to CSV file.
    """
    try:
        fname = f"export_{user_role}_{user_id}_{self.request.id}.csv"
        path = os.path.join(EXPORT_DIR, fname)

        with open(path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)

            if user_role == 'student':
                writer.writerow(['Application ID', 'Company', 'Drive Title', 'Status', 'Applied At'])
                # map user_id -> student.id (user_id in this case is a User.id passed by API)
                student = Student.query.filter_by(user_id=user_id).first()
                if not student:
                    return {'status':'error','msg':'Student profile not found'}
                # select explicit scalar columns to avoid ORM-row packing differences across contexts
                apps = db.session.query(Application.id, Company.name.label('company_name'), PlacementDrive.title.label('drive_title'), Application.status, Application.applied_at).join(PlacementDrive, Application.drive_id == PlacementDrive.id).outerjoin(Company, PlacementDrive.company_id == Company.id).filter(Application.student_id == student.id).all()
                for app_row in apps:
                    # app_row is a tuple (id, company_name, drive_title, status, applied_at)
                    try:
                        app_id, company_name, drive_title, status, applied_at = app_row
                    except Exception:
                        # fallback: coerce to list and pad
                        vals = list(app_row) + [None]*5
                        app_id, company_name, drive_title, status, applied_at = vals[:5]
                    writer.writerow([app_id, company_name or '', drive_title or '', status or '', applied_at or ''])

            elif user_role == 'company':
                writer.writerow(['Application ID', 'Student Name', 'Drive Title', 'Status', 'Applied At'])
                # here user_id is a Company.id
                comp = Company.query.get(user_id)
                if not comp:
                    return {'status':'error','msg':'Company profile not found'}
                apps = db.session.query(Application.id, User.email.label('student_email'), PlacementDrive.title.label('drive_title'), Application.status, Application.applied_at).join(PlacementDrive, Application.drive_id == PlacementDrive.id).filter(PlacementDrive.company_id == comp.id).join(Student, Application.student_id == Student.id).join(User, Student.user_id == User.id).all()
                for app_row in apps:
                    try:
                        app_id, student_identifier, drive_title, status, applied_at = app_row
                    except Exception:
                        vals = list(app_row) + [None]*5
                        app_id, student_identifier, drive_title, status, applied_at = vals[:5]
                    writer.writerow([app_id, student_identifier or '', drive_title or '', status or '', applied_at or ''])

            else:
                # unknown role
                return {'status': 'error', 'msg': 'Unknown role'}

        # attempt to email the user a copy
        try:
            if user_role == 'student':
                user = User.query.get(user_id)
                recipient = user.email if user else None
            else:
                comp = Company.query.get(user_id)
                recipient = comp.hr_contact if comp and comp.hr_contact else (comp.name + '@example.com' if comp else None)

            if recipient:
                subject = 'Your application export is ready'
                # include a direct download link and attempt to attach the file
                base = current_app.config.get('BASE_URL', 'http://localhost:5000')
                link = f"{base.rstrip('/')}/api/tasks/download_export/{self.request.id}"
                body = f'Attached is the CSV export you requested. You can also download it here: {link}'
                msg = Message(subject=subject, recipients=[recipient], body=body)
                # attach if file present
                try:
                    if os.path.exists(path) and os.path.getsize(path) > 0:
                        with open(path, 'rb') as fp:
                            msg.attach(fname, 'text/csv', fp.read())
                    else:
                        # include CSV content inline if file empty
                        with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                            content = fp.read()
                        body += '\n\nCSV CONTENT:\n' + (content or '(empty)')
                        msg.body = body
                except Exception as e:
                    current_app.logger.exception('Failed attaching file: %s', e)
                mail.send(msg)
        except Exception as e:
            current_app.logger.exception('Failed to email export: %s', e)

        return {'status': 'success', 'path': path, 'filename': fname}
    except Exception as e:
        current_app.logger.exception('export_applications_csv failed: %s', e)
        return {'status': 'error', 'msg': str(e)}


@celery.task()
def send_interview_reminders():
    """Find interviews scheduled in the next 24 hours and send reminders to students.
    Uses email and optional GChat webhook if configured.
    """
    now = datetime.datetime.utcnow()
    window_end = now + datetime.timedelta(hours=24)

    # Interviews scheduled in next 24 hours
    upcoming = Interview.query.filter(Interview.scheduled_at >= now, Interview.scheduled_at <= window_end).all()
    sent = 0
    for inv in upcoming:
        try:
            app_obj = Application.query.get(inv.application_id)
            if not app_obj:
                continue
            student_profile = Student.query.get(app_obj.student_id)
            if not student_profile:
                continue
            student_user = User.query.get(student_profile.user_id)
            drive = PlacementDrive.query.get(app_obj.drive_id)
            company = Company.query.get(drive.company_id) if drive else None

            recipient_email = student_user.email if student_user else None
            if not recipient_email:
                continue

            scheduled_when = inv.scheduled_at
            subject = f"Interview Reminder: {drive.title if drive else 'Drive'}"
            body = f"Dear {student_profile.name or student_user.email},\n\nThis is a reminder for your upcoming interview for '{drive.title if drive else ''}' with {company.name if company else ''}.\n\nScheduled at: {scheduled_when}\nRound: {inv.interview_round or ''}\n\nPlease be on time.\n\nBest regards,\nPlacement Cell"
            msg = Message(subject=subject, recipients=[recipient_email], body=body)
            mail.send(msg)
            sent += 1

            # optional webhook
            webhook = current_app.config.get('GCHAT_WEBHOOK_URL')
            if webhook:
                try:
                    import requests
                    payload = {'text': body}
                    requests.post(webhook, json=payload, timeout=5)
                except Exception:
                    current_app.logger.exception('Failed to post webhook')
        except Exception:
            current_app.logger.exception('Failed to send reminder for interview %s', getattr(inv, 'id', ''))

    return {'status': 'done', 'sent': sent}


@celery.task()
def generate_monthly_placement_report():
    """Generate a monthly HTML report for admin/companies and email to admin."
    Currently attaches HTML file; PDF generation can be added later.
    """
    try:
        # compute basic stats for the previous month (based on applications timestamp)
        today = datetime.date.today()
        first_of_month = today.replace(day=1)
        prev_month_end = first_of_month - datetime.timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        start_dt = datetime.datetime.combine(prev_month_start, datetime.time.min)
        end_dt = datetime.datetime.combine(prev_month_end, datetime.time.max)

        # number of drives with activity in the month (distinct drives with applications)
        drives_count = db.session.query(PlacementDrive.id).join(Application, Application.drive_id == PlacementDrive.id).filter(Application.applied_at >= start_dt, Application.applied_at <= end_dt).distinct().count()
        # applications
        applications_count = Application.query.filter(Application.applied_at >= start_dt, Application.applied_at <= end_dt).count()
        # placements (placed records with created_at if present else all placements)
        # Placement has no created_at column in current schema; count all placements whose joining_date falls in the month
        placements_count = Placement.query.filter(Placement.joining_date >= start_dt, Placement.joining_date <= end_dt).count()

        # simple per-company stats (drives and applications)
        per_company = db.session.query(Company.name,
                                       func.count(func.distinct(PlacementDrive.id)).label('drives'),
                                       func.count(Application.id).label('applications'))
        per_company = per_company.join(PlacementDrive, PlacementDrive.company_id == Company.id).outerjoin(Application, Application.drive_id == PlacementDrive.id)
        per_company = per_company.filter(Application.applied_at >= start_dt, Application.applied_at <= end_dt).group_by(Company.id).all()

        # render HTML using a simple inline template
        html = render_template_string('''
        <html><body>
        <h1>Monthly Placement Report: {{ month }}</h1>
        <p>Drives: {{ drives_count }} | Applications: {{ applications_count }} | Placements: {{ placements_count }}</p>
        <h2>Per-company summary</h2>
        <table border="1" cellpadding="6">
        <tr><th>Company</th><th>Drives</th><th>Applications</th></tr>
        {% for c in per_company %}
          <tr><td>{{ c[0] }}</td><td>{{ c[1] }}</td><td>{{ c[2] }}</td></tr>
        {% endfor %}
        </table>
        </body></html>
        ''', month=prev_month_start.strftime('%B %Y'), drives_count=drives_count, applications_count=applications_count, placements_count=placements_count, per_company=per_company)

        # write file
        reports_dir = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        filename = f"monthly_report_{prev_month_start.strftime('%Y_%m')}.html"
        path = os.path.join(reports_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)

        # email admin
        admin_email = current_app.config.get('MAIL_DEFAULT_SENDER')
        admin_recipients = [admin_email] if admin_email else []
        # optionally use configured ADMIN_EMAIL
        if current_app.config.get('ADMIN_EMAIL'):
            admin_recipients = [current_app.config.get('ADMIN_EMAIL')]

        if admin_recipients:
            msg = Message(subject=f"Monthly Placement Report - {prev_month_start.strftime('%B %Y')}", recipients=admin_recipients, html=html)
            with open(path, 'rb') as fp:
                msg.attach(filename, 'text/html', fp.read())
            mail.send(msg)

        return {'status': 'success', 'path': path}
    except Exception as e:
        current_app.logger.exception('generate_monthly_placement_report failed: %s', e)
        return {'status': 'error', 'msg': str(e)}
