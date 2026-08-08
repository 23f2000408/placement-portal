from flask import Blueprint, request, jsonify
from utils import role_required
from db import db
from models import Company, User, PlacementDrive

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/companies/pending', methods=['GET'])
@role_required('admin')
def pending_companies():
    comps = Company.query.filter_by(approved=False).all()
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
    drives = PlacementDrive.query.filter(PlacementDrive.status != 'Approved').all()
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
