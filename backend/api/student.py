from flask import Blueprint, jsonify
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
        out.append({'id': a.id, 'student_id': a.student_id, 'drive_id': a.drive_id, 'drive_title': a.drive.title if a.drive else None, 'status': a.status, 'applied_at': a.applied_at.isoformat() if a.applied_at else None})
    return jsonify({'applications': out}),200
