from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import db
from models import PlacementDrive, Company, Student, Application, Interview
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
    # require enhanced fields at creation time
    salary = data.get('salary')
    benefits = data.get('benefits')
    required_skills = data.get('required_skills')
    required_experience = data.get('required_experience')
    if not salary or not benefits or not required_skills or not required_experience:
        return jsonify({'msg':'salary, benefits, required_skills and required_experience are required'}),400
    drive = PlacementDrive(company_id=company.id, title=title, description=data.get('description'), eligibility=data.get('eligibility'), application_deadline=ad, status='Pending', salary=salary, benefits=benefits, required_skills=required_skills, required_experience=required_experience, drive_status=data.get('drive_status','Active'), extra=data.get('extra'))
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
        apps.append({
            'id': a.id,
            'student_id': a.student_id,
            'student_name': a.student.name,
            'student_email': a.student.user.email if a.student.user else None,
            'student_cgpa': a.student.cgpa,
            'student_contact': a.student.contact_number,
            'resume_path': a.student.resume_path,
            'status': a.status,
            'applied_at': a.applied_at.isoformat() if a.applied_at else None,
            # include profile fields so company UI can show details
            'education': getattr(a.student, 'education', None),
            'skills': getattr(a.student, 'skills', None),
            'experience': getattr(a.student, 'experience', None),
            # also include nested student object minimal fields
            'student': {
                'id': a.student.id,
                'name': a.student.name,
                'email': a.student.user.email if a.student.user else None,
                'cgpa': a.student.cgpa,
                'contact_number': a.student.contact_number,
                'education': getattr(a.student, 'education', None),
                'skills': getattr(a.student, 'skills', None),
                'experience': getattr(a.student, 'experience', None),
                'resume_path': a.student.resume_path
            }
        })
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
    # allowed decisions expanded to support workflow: Applied / Shortlisted / Interview / Offer / Rejected / Placed
    allowed = ('Shortlisted','Interview','Offer','Rejected','Placed')
    if decision not in allowed:
        return jsonify({'msg':"decision must be one of %s" % (', '.join(allowed))}),400
    # prevent state change if already Rejected
    if app.status == 'Rejected' and decision != 'Rejected':
        return jsonify({'msg':'cannot change decision for a rejected application'}),400

    # handle Offer specially: capture optional offer_message and generate offer letter text
    if decision == 'Offer':
        offer_message = data.get('offer_message')
        # build a generic template
        student_name = app.student.name if app.student else 'Student'
        company_name = company.name if company else 'Company'
        role = app.drive.title if app.drive else 'Role'
        default_template = (
            f"Dear {student_name},\n\n"
            f"We are pleased to offer you the position of {role} at {company_name}.\n\n"
            "Please find the key details below:\n"
            f"Position: {role}\n"
            f"Company: {company_name}\n"
            f"Salary: {app.drive.salary if app.drive and app.drive.salary else 'TBD'}\n\n"
            "Please confirm your acceptance by replying to this message.\n\n"
            "Best regards,\n")
        # append company-provided message if present
        if offer_message:
            full_text = default_template + "\n" + offer_message + "\n"
        else:
            full_text = default_template
        # attach into application extra
        extra = app.extra or {}
        extra['offer_letter'] = {'text': full_text, 'generated_at': datetime.utcnow().isoformat()}
        app.extra = extra
        app.status = 'Offer'
        db.session.add(app)
        db.session.commit()
        return jsonify({'msg':'offer created and application updated','status':app.status}),200

    # regular decisions
    app.status = decision
    db.session.add(app)
    # if placed, create a Placement record if not exists
    if decision == 'Placed':
        from models import Placement
        existing_place = Placement.query.filter_by(student_id=app.student_id, company_id=company.id, position=app.drive.title if app.drive else None).first()
        if not existing_place:
            placement = Placement(student_id=app.student_id, company_id=company.id, position=app.drive.title if app.drive else None, salary=app.drive.salary if app.drive else None, joining_date=None)
            db.session.add(placement)
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
    # drive must be active
    if hasattr(drive, 'drive_status') and drive.drive_status != 'Active':
        return jsonify({'msg':'drive is not accepting applications'}),403
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


# Enhanced job posting fields (salary, benefits, skills, experience)
@drives_bp.route('/<int:drive_id>', methods=['PUT'])
@role_required('company')
def update_drive(drive_id):
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    company = Company.query.filter_by(user_id=user_id).first()
    if not company:
        return jsonify({'msg':'company profile not found'}),400
    drive = PlacementDrive.query.get(drive_id)
    if not drive or drive.company_id != company.id:
        return jsonify({'msg':'drive not found or access denied'}),404
    data = request.get_json() or {}
    if 'salary' in data:
        drive.salary = data.get('salary')
    if 'benefits' in data:
        drive.benefits = data.get('benefits')
    if 'required_skills' in data:
        drive.required_skills = data.get('required_skills')
    if 'required_experience' in data:
        drive.required_experience = data.get('required_experience')
    if 'drive_status' in data:
        drive.drive_status = data.get('drive_status')  # Active, Closed
    db.session.add(drive)
    db.session.commit()
    return jsonify({'msg':'drive updated'}),200


# Schedule interview for an application
@drives_bp.route('/company/applications/<int:application_id>/schedule_interview', methods=['POST'])
@role_required('company')
def schedule_interview(application_id):
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    company = Company.query.filter_by(user_id=user_id).first()
    if not company:
        return jsonify({'msg':'company profile not found'}),400
    app = Application.query.get(application_id)
    if not app:
        return jsonify({'msg':'application not found'}),404
    if app.drive.company_id != company.id:
        return jsonify({'msg':'not allowed'}),403
    data = request.get_json() or {}
    scheduled_at = data.get('scheduled_at')
    interview_round = data.get('interview_round','Round 1')
    if not scheduled_at:
        return jsonify({'msg':'scheduled_at required (ISO format)'}),400
    try:
        dt = datetime.fromisoformat(scheduled_at)
    except Exception:
        return jsonify({'msg':'invalid date format'}),400
    interview = Interview(application_id=app.id, scheduled_at=dt, interview_round=interview_round, result='Pending')
    db.session.add(interview)
    # set application status to Interview when scheduling
    try:
        app.status = 'Interview'
        db.session.add(app)
    except Exception:
        pass
    db.session.commit()
    return jsonify({'msg':'interview scheduled', 'interview_id': interview.id}),201


# Add feedback to an interview
@drives_bp.route('/company/interviews/<int:interview_id>/feedback', methods=['POST'])
@role_required('company')
def add_interview_feedback(interview_id):
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    company = Company.query.filter_by(user_id=user_id).first()
    if not company:
        return jsonify({'msg':'company profile not found'}),400
    interview = Interview.query.get(interview_id)
    if not interview:
        return jsonify({'msg':'interview not found'}),404
    if interview.application.drive.company_id != company.id:
        return jsonify({'msg':'not allowed'}),403
    data = request.get_json() or {}
    feedback = data.get('feedback')
    result = data.get('result')  # Pass, Fail, Pending
    if feedback:
        interview.feedback = feedback
    if result in ('Pass','Fail','Pending'):
        interview.result = result
    db.session.add(interview)
    db.session.commit()
    return jsonify({'msg':'feedback added'}),200


# Get interviews for an application (student view)
@drives_bp.route('/student/applications/<int:application_id>/interviews', methods=['GET'])
@role_required('student')
def get_application_interviews(application_id):
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'msg':'student profile not found'}),400
    app = Application.query.get(application_id)
    if not app or app.student_id != student.id:
        return jsonify({'msg':'application not found or access denied'}),404
    interviews = Interview.query.filter_by(application_id=app.id).all()
    out = []
    for i in interviews:
        out.append({
            'id': i.id,
            'round': i.interview_round,
            'scheduled_at': i.scheduled_at.isoformat() if i.scheduled_at else None,
            'feedback': i.feedback,
            'result': i.result,
        })
    return jsonify({'interviews': out}),200


@drives_bp.route('/student/applications/<int:application_id>/offer', methods=['GET'])
@role_required('student')
def get_application_offer(application_id):
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'msg':'student profile not found'}),400
    app = Application.query.get(application_id)
    if not app or app.student_id != student.id:
        return jsonify({'msg':'application not found or access denied'}),404
    extra = app.extra or {}
    offer = extra.get('offer_letter') if isinstance(extra, dict) else None
    if not offer:
        return jsonify({'msg':'no offer found for this application'}),404
    return jsonify({'offer': offer}),200


@drives_bp.route('/student/applications/<int:application_id>/offer/download', methods=['GET'])
@role_required('student')
def download_application_offer(application_id):
    from flask import Response
    user_id = get_jwt_identity()
    try:
        user_id = int(user_id)
    except Exception:
        pass
    student = Student.query.filter_by(user_id=user_id).first()
    if not student:
        return jsonify({'msg':'student profile not found'}),400
    app = Application.query.get(application_id)
    if not app or app.student_id != student.id:
        return jsonify({'msg':'application not found or access denied'}),404
    extra = app.extra or {}
    offer = extra.get('offer_letter') if isinstance(extra, dict) else None
    if not offer or not offer.get('text'):
        return jsonify({'msg':'no offer found for this application'}),404
    text = offer.get('text')
    filename = f"offer_application_{application_id}.txt"
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return Response(text, mimetype='text/plain', headers=headers)

