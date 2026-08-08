from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from db import db
from models import PlacementDrive, Company
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
