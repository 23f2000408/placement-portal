from flask import Blueprint, request, jsonify
from utils import role_required
from db import db
from models import Company, User, PlacementDrive, Student, Application
from sqlalchemy import or_
from flask import request

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/companies/pending', methods=['GET'])
@role_required('admin')
def pending_companies():
    # return companies that are awaiting admin decision: not approved and user still active
    comps = Company.query.join(User).filter(Company.approved==False, User.is_active==True).all()
    out = []
    for c in comps:
        out.append({'id': c.id, 'name': c.name, 'hr_contact': c.hr_contact, 'website': c.website, 'user_id': c.user_id})
    return jsonify({'pending': out}), 200

@admin_bp.route('/companies/<int:company_id>/approve', methods=['POST'])
@role_required('admin')
def approve_company(company_id):
    c = Company.query.get(company_id)
    if not c:
        return jsonify({'msg':'company not found'}),404
    c.approved = True
    db.session.add(c)
    db.session.commit()
    return jsonify({'msg':'company approved'}),200

@admin_bp.route('/companies/<int:company_id>/reject', methods=['POST'])
@role_required('admin')
def reject_company(company_id):
    c = Company.query.get(company_id)
    if not c:
        return jsonify({'msg':'company not found'}),404
    # soft-delete: deactivate user and company
    user = User.query.get(c.user_id)
    if user:
        user.is_active = False
        db.session.add(user)
    c.approved = False
    db.session.add(c)
    db.session.commit()
    return jsonify({'msg':'company rejected/deactivated'}),200


# Drives approval/rejection
@admin_bp.route('/drives/pending', methods=['GET'])
@role_required('admin')
def pending_drives():
    # only show drives that are explicitly pending admin approval
    drives = PlacementDrive.query.filter_by(status='Pending').all()
    out = []
    for d in drives:
        out.append({
            'id': d.id,
            'company_id': d.company_id,
            'company_name': d.company.name if d.company else None,
            'title': d.title,
            'description': d.description,
            'application_deadline': d.application_deadline.isoformat() if d.application_deadline else None,
            'status': d.status,
            'eligibility': d.eligibility,
        })
    return jsonify({'pending_drives': out}), 200

@admin_bp.route('/drives/<int:drive_id>/approve', methods=['POST'])
@role_required('admin')
def approve_drive(drive_id):
    d = PlacementDrive.query.get(drive_id)
    if not d:
        return jsonify({'msg':'drive not found'}),404
    d.status = 'Approved'
    db.session.add(d)
    db.session.commit()
    return jsonify({'msg':'drive approved'}),200

@admin_bp.route('/drives/<int:drive_id>/reject', methods=['POST'])
@role_required('admin')
def reject_drive(drive_id):
    d = PlacementDrive.query.get(drive_id)
    if not d:
        return jsonify({'msg':'drive not found'}),404
    d.status = 'Rejected'
    db.session.add(d)
    db.session.commit()
    return jsonify({'msg':'drive rejected'}),200

# All companies
@admin_bp.route('/companies', methods=['GET'])
@role_required('admin')
def list_companies():
    comps = Company.query.all()
    out = []
    for c in comps:
        out.append({'id': c.id, 'name': c.name, 'hr_contact': c.hr_contact, 'website': c.website, 'approved': c.approved, 'user_id': c.user_id})
    return jsonify({'companies': out}), 200

# All students
@admin_bp.route('/students', methods=['GET'])
@role_required('admin')
def list_students():
    studs = Student.query.all()
    out = []
    for s in studs:
        out.append({'student_id': s.id, 'user_id': s.user_id, 'name': s.name, 'branch': s.branch, 'cgpa': s.cgpa, 'year': s.year, 'resume_path': s.resume_path})
    return jsonify({'students': out}), 200

# Deactivate / blacklist company
@admin_bp.route('/companies/<int:company_id>/deactivate', methods=['POST'])
@role_required('admin')
def deactivate_company(company_id):
    c = Company.query.get(company_id)
    if not c:
        return jsonify({'msg':'company not found'}),404
    user = User.query.get(c.user_id)
    if user:
        user.is_active = False
        db.session.add(user)
    c.approved = False
    db.session.add(c)
    db.session.commit()
    return jsonify({'msg':'company deactivated'}),200

# Deactivate / blacklist student
@admin_bp.route('/students/<int:student_id>/deactivate', methods=['POST'])
@role_required('admin')
def deactivate_student(student_id):
    s = Student.query.get(student_id)
    if not s:
        return jsonify({'msg':'student not found'}),404
    user = User.query.get(s.user_id)
    if user:
        user.is_active = False
        db.session.add(user)
    db.session.commit()
    return jsonify({'msg':'student deactivated'}),200

# Search companies/students
@admin_bp.route('/search/companies', methods=['GET'])
@role_required('admin')
def search_companies():
    q = request.args.get('q','')
    if not q:
        return list_companies()
    comps = Company.query.filter(or_(Company.name.ilike(f"%{q}%"), Company.website.ilike(f"%{q}%"))).all()
    out = [{'id': c.id, 'name': c.name, 'approved': c.approved, 'website': c.website} for c in comps]
    return jsonify({'companies': out}),200

@admin_bp.route('/search/students', methods=['GET'])
@role_required('admin')
def search_students():
    q = request.args.get('q','')
    if not q:
        return list_students()
    studs = Student.query.filter(or_(Student.name.ilike(f"%{q}%"))).all()
    out = [{'student_id': s.id, 'name': s.name, 'branch': s.branch, 'cgpa': s.cgpa} for s in studs]
    return jsonify({'students': out}),200

# Applications
@admin_bp.route('/applications', methods=['GET'])
@role_required('admin')
def list_applications():
    apps = Application.query.all()
    out = []
    for a in apps:
        # skip applications from deactivated students
        if not a.student or not a.student.user.is_active:
            continue
        out.append({'id': a.id, 'student_id': a.student_id, 'student_name': a.student.name if a.student else None, 'drive_id': a.drive_id, 'drive_title': a.drive.title if a.drive else None, 'status': a.status, 'applied_at': a.applied_at.isoformat() if a.applied_at else None})
    return jsonify({'applications': out}),200

# Applications per company
@admin_bp.route('/companies/<int:company_id>/applications', methods=['GET'])
@role_required('admin')
def company_applications(company_id):
    # find drives for company then applications
    drives = PlacementDrive.query.filter_by(company_id=company_id).all()
    drive_ids = [d.id for d in drives]
    apps = Application.query.filter(Application.drive_id.in_(drive_ids)).all() if drive_ids else []
    out = [{'id': a.id, 'student_id': a.student_id, 'student_name': a.student.name if a.student else None, 'drive_id': a.drive_id, 'drive_title': a.drive.title if a.drive else None, 'status': a.status} for a in apps]
    return jsonify({'applications': out}),200
