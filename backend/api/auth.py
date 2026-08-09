from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from db import db
from models import User, Student, Company
from datetime import timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register/student', methods=['POST'])
def register_student():
    try:
        data = request.get_json(force=True) or {}
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        cgpa = data.get('cgpa')
        contact = data.get('contact_number')
        resume = data.get('resume_path')
        # resume optional at registration
        if not email or not password or not name or cgpa is None or not contact:
            return jsonify({'msg':'email,password,name,cgpa and contact_number required'}),400
        if User.query.filter_by(email=email).first():
            return jsonify({'msg':'email exists'}),400
        user = User(email=email, password_hash=generate_password_hash(password), role='student', is_active=True)
        db.session.add(user)
        db.session.flush()
        student = Student(user_id=user.id, name=name, cgpa=float(cgpa), contact_number=contact, resume_path=resume)
        db.session.add(student)
        db.session.commit()
        return jsonify({'msg':'student registered'}),201
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg':'error','error':str(e)}),500

@auth_bp.route('/register/company', methods=['POST'])
def register_company():
    try:
        data = request.get_json(force=True) or {}
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        if not email or not password or not name:
            return jsonify({'msg':'email, password and name required'}),400
        if User.query.filter_by(email=email).first():
            return jsonify({'msg':'email exists'}),400
        user = User(email=email, password_hash=generate_password_hash(password), role='company', is_active=True)
        db.session.add(user)
        db.session.flush()
        company = Company(user_id=user.id, name=name, hr_contact=data.get('hr_contact'), website=data.get('website'), approved=False)
        db.session.add(company)
        db.session.commit()
        return jsonify({'msg':'company registered, pending admin approval'}),201
    except Exception as e:
        db.session.rollback()
        return jsonify({'msg':'error','error':str(e)}),500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json(force=True) or {}
        email = data.get('email')
        password = data.get('password')
        if not email or not password:
            return jsonify({'msg':'email and password required'}),400
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'msg':'invalid credentials'}),401
        additional_claims = {'role': user.role}
        # store identity as string to satisfy JWT subject requirement
        access_token = create_access_token(identity=str(user.id), additional_claims=additional_claims, expires_delta=timedelta(hours=12))
        return jsonify({'access_token': access_token, 'role': user.role, 'is_active': user.is_active}),200
    except Exception as e:
        return jsonify({'msg':'error','error':str(e)}),500

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    try:
        identity = get_jwt_identity()
        try:
            identity = int(identity)
        except Exception:
            pass
        user = User.query.get(identity)
        if not user:
            return jsonify({'msg':'user not found'}),404
        data = {'id': user.id, 'email': user.email, 'role': user.role, 'is_active': user.is_active}
        # attach profile details for student/company
        if user.role == 'student':
            s = Student.query.filter_by(user_id=user.id).first()
            if s:
                data['student'] = {'id': s.id, 'name': s.name, 'cgpa': s.cgpa, 'contact_number': s.contact_number, 'resume_path': s.resume_path}
        if user.role == 'company':
            c = Company.query.filter_by(user_id=user.id).first()
            if c:
                data['company'] = {'id': c.id, 'name': c.name, 'approved': c.approved, 'website': c.website, 'hr_contact': c.hr_contact}
        return jsonify({'user': data}),200
    except Exception as e:
        return jsonify({'msg':'error','error':str(e)}),500
