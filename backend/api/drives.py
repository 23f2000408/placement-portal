from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import db
from models import PlacementDrive, Company, Student, Application
from utils import role_required
from datetime import datetime

drives_bp = Blueprint('drives', __name__)

@drives_bp.route('/', methods=['GET'])
def list_drives():
    # Public list: only Approved and not closed
    drives = PlacementDrive.query.filter(PlacementDrive.status=='Approved').all()
    out = []
    for d in drives:
        out.append({
            'id': d.id,
            'company_id': d.company_id,
            'company_name': d.company.name if d.company else None,
            'title': d.title,
            'description': d.description,
            'eligibility': d.eligibility,
            'application_deadline': d.application_deadline.isoformat() if d.application_deadline else None,
            'status': d.status,
            'extra': d.extra,
        })
    return jsonify({'drives': out}), 200

@drives_bp.route('/create', methods=['POST'])
@role_required('company')
def create_drive():
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    company = Company.query.filter_by(user_id=user_id).first()
    if not company:
        return jsonify({'msg':'company profile not found'}),400
    # prevent deactivated companies from creating drives
    if not company.user.is_active:
        return jsonify({'msg':'company account deactivated'}),403
    if not company.approved:
        return jsonify({'msg':'company not approved by admin yet'}),403
    data = request.get_json() or {}
    title = data.get('title')
    if not title:
        return jsonify({'msg':'title required'}),400
    dd = data.get('application_deadline')
    ad = None
    if dd:
        try:
            ad = datetime.fromisoformat(dd)
        except Exception:
            return jsonify({'msg':'invalid date format, use ISO'}),400
    drive = PlacementDrive(company_id=company.id, title=title, description=data.get('description'), eligibility=data.get('eligibility'), application_deadline=ad, status='Pending', extra=data.get('extra'))
    db.session.add(drive)
    db.session.commit()
    return jsonify({'msg':'drive created', 'drive_id': drive.id}),201

# Company-specific endpoints
@drives_bp.route('/company/drives', methods=['GET'])
@role_required('company')
def company_drives():
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    company = Company.query.filter_by(user_id=user_id).first()
    if not company:
        return jsonify({'msg':'company profile not found'}),400
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()
    out = {'pending': [], 'approved': [], 'rejected': []}
    for d in drives:
        item = {'id': d.id, 'title': d.title, 'description': d.description, 'application_deadline': d.application_deadline.isoformat() if d.application_deadline else None, 'status': d.status}
        if d.status == 'Approved':
            out['approved'].append(item)
        elif d.status == 'Rejected':
            out['rejected'].append(item)
        else:
            out['pending'].append(item)
    return jsonify(out),200

@drives_bp.route('/company/drives/<int:drive_id>/applications', methods=['GET'])
@role_required('company')
def company_drive_applications(drive_id):
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    company = Company.query.filter_by(user_id=user_id).first()
    if not company:
        return jsonify({'msg':'company profile not found'}),400
    if not company.user.is_active:
        return jsonify({'msg':'company account deactivated'}),403
    drive = PlacementDrive.query.get(drive_id)
    if not drive or drive.company_id != company.id:
        return jsonify({'msg':'drive not found or access denied'}),404
    apps = []
    for a in drive.applications:
        # skip applications from deactivated students
        if not a.student or not a.student.user.is_active:
            continue
        apps.append({'id': a.id, 'student_id': a.student_id, 'student_name': a.student.name, 'student_email': a.student.user.email if a.student.user else None, 'student_cgpa': a.student.cgpa, 'student_contact': a.student.contact_number, 'resume_path': a.student.resume_path, 'status': a.status, 'applied_at': a.applied_at.isoformat() if a.applied_at else None})
    return jsonify({'applications': apps}),200

@drives_bp.route('/company/applications/<int:application_id>/decide', methods=['POST'])
@role_required('company')
def company_decide_application(application_id):
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    company = Company.query.filter_by(user_id=user_id).first()
    if not company:
        return jsonify({'msg':'company profile not found'}),400
    if not company.user.is_active:
        return jsonify({'msg':'company account deactivated'}),403
    app = Application.query.get(application_id)
    if not app:
        return jsonify({'msg':'application not found'}),404
    drive = app.drive
    if not drive or drive.company_id != company.id:
        return jsonify({'msg':'not allowed'}),403
    data = request.get_json() or {}
    decision = data.get('decision')
    if decision not in ('Accepted','Rejected','Shortlisted'):
        return jsonify({'msg':'decision must be Accepted, Rejected or Shortlisted'}),400
    app.status = decision
    db.session.add(app)
    db.session.commit()
    return jsonify({'msg':'application updated','status':app.status}),200

@drives_bp.route('/<int:drive_id>', methods=['GET'])
def get_drive(drive_id):
    d = PlacementDrive.query.get(drive_id)
    if not d:
        return jsonify({'msg':'not found'}),404
    return jsonify({
        'id': d.id,
        'company_id': d.company_id,
        'company_name': d.company.name if d.company else None,
        'title': d.title,
        'description': d.description,
        'eligibility': d.eligibility,
        'application_deadline': d.application_deadline.isoformat() if d.application_deadline else None,
        'status': d.status,
        'extra': d.extra,
    }),200

@drives_bp.route('/<int:drive_id>/apply', methods=['POST'])
@role_required('student')
def apply_drive(drive_id):
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'msg':'student profile not found'}),400
    # prevent deactivated students from applying
    if not student.user.is_active:
        return jsonify({'msg':'student account deactivated'}),403
    drive = PlacementDrive.query.get(drive_id)
    if not drive:
        return jsonify({'msg':'drive not found'}),404
    if drive.status != 'Approved':
        return jsonify({'msg':'cannot apply to unapproved drive'}),403
    if drive.application_deadline and drive.application_deadline < datetime.utcnow():
        return jsonify({'msg':'application deadline passed'}),400
    # ensure resume present (student or provided in request)
    data = request.get_json() or {}
    if not student.resume_path:
        resume = data.get('resume_path')
        if not resume:
            return jsonify({'msg':'resume required to apply'}),400
        # update student resume_path
        student.resume_path = resume
        db.session.add(student)
        db.session.commit()
    # prevent duplicate
    existing = Application.query.filter_by(student_id=student.id, drive_id=drive.id).first()
    if existing:
        return jsonify({'msg':'already applied'}),400
    app = Application(student_id=student.id, drive_id=drive.id, status='Applied')
    db.session.add(app)
    db.session.commit()
    return jsonify({'msg':'application submitted', 'application_id': app.id}),201
