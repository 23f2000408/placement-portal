from flask import Blueprint, jsonify, request
from utils import role_required
from db import db
from models import Student, Application
from flask_jwt_extended import get_jwt_identity

student_bp = Blueprint('student', __name__)

@student_bp.route('/applications', methods=['GET'])
@role_required('student')
def my_applications():
    identity = get_jwt_identity()
    try:
        identity = int(identity)
    except Exception:
        pass
    student = Student.query.filter_by(user_id=identity).first()
    if not student:
        return jsonify({'msg':'student profile not found'}),400
    apps = Application.query.filter_by(student_id=student.id).all()
    out = []
    for a in apps:
        # include offer text if present in extra
        offer_text = None
        try:
            extra = a.extra or {}
            if isinstance(extra, dict) and 'offer_letter' in extra:
                offer_text = extra['offer_letter'].get('text') if extra['offer_letter'] else None
        except Exception:
            offer_text = None
        out.append({'id': a.id, 'student_id': a.student_id, 'drive_id': a.drive_id, 'drive_title': a.drive.title if a.drive else None, 'company_name': a.drive.company.name if a.drive and a.drive.company else None, 'status': a.status, 'applied_at': a.applied_at.isoformat() if a.applied_at else None, 'offer_letter': offer_text})
    # include placement history for this student
    from models import Placement, Company
    placements = Placement.query.filter_by(student_id=student.id).all()
    place_out = []
    for p in placements:
        comp = Company.query.get(p.company_id)
        place_out.append({'placement_id': p.id, 'company_id': p.company_id, 'company_name': comp.name if comp else None, 'position': p.position, 'salary': p.salary, 'joining_date': p.joining_date.isoformat() if p.joining_date else None})
    return jsonify({'applications': out, 'placements': place_out}),200


@student_bp.route('/profile', methods=['PUT'])
@role_required('student')
def update_profile():
    identity = get_jwt_identity()
    try:
        identity = int(identity)
    except Exception:
        pass
    student = Student.query.filter_by(user_id=identity).first()
    if not student:
        return jsonify({'msg':'student profile not found'}),400
    data = request.get_json() or {}
    if 'name' in data:
        student.name = data.get('name')
    if 'education' in data:
        student.education = data.get('education')
    if 'skills' in data:
        student.skills = data.get('skills')
    if 'experience' in data:
        student.experience = data.get('experience')
    if 'cgpa' in data:
        student.cgpa = data.get('cgpa')
    if 'resume_path' in data:
        student.resume_path = data.get('resume_path')
    db.session.add(student)
    db.session.commit()
    return jsonify({'msg':'profile updated'}),200
