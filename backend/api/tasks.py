from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from tasks import export_applications_csv, celery
from models import User, Company

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/export_applications', methods=['POST'])
@jwt_required()
def trigger_export():
    """Trigger CSV export for the current user (student) or company. Returns task id."""
    identity = get_jwt_identity()
    # identity is user id string or int
    user_id = identity
    # role stored in JWT additional claims
    claims = get_jwt()
    role = claims.get('role') if isinstance(claims, dict) else None

    # For company, allow company exports as well
    if role == 'company':
        # map to company id
        comp = Company.query.filter(Company.user_id == int(user_id)).first()
        if not comp:
            return jsonify({'msg': 'Company not found'}), 404
        target_id = comp.id
        user_role = 'company'
    else:
        # default assume student
        try:
            target_id = int(user_id)
        except Exception:
            target_id = user_id
        user_role = 'student'

    task = export_applications_csv.apply_async(args=[target_id, user_role])
    return jsonify({'task_id': task.id, 'status': 'queued'})


@tasks_bp.route('/status/<task_id>')
@jwt_required()
def task_status(task_id):
    # Restrict visibility: only owner (student/company) or admin can view status
    identity = get_jwt_identity()
    req_user_id = None
    try:
        req_user_id = int(identity)
    except Exception:
        req_user_id = identity
    claims = get_jwt()
    req_role = claims.get('role') if isinstance(claims, dict) else None

    res = celery.AsyncResult(task_id)

    # If admin, allow
    if req_role == 'admin':
        info = {'id': task_id, 'state': res.state, 'info': res.info}
        return jsonify(info)

    # otherwise ensure the task belongs to this user (filename encodes role and id)
    import os
    exports_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'exports')
    for f in os.listdir(exports_dir):
        if task_id in f:
            # expected filename format: export_{role}_{id}_{taskid}.csv
            parts = f.split('_')
            if len(parts) >= 4:
                f_role = parts[1]
                f_id_part = parts[2]
                try:
                    f_id = int(f_id_part)
                except Exception:
                    f_id = f_id_part
                allowed = False
                if req_role == 'company' and f_role == 'company':
                    # confirm this company belongs to the requesting user
                    comp = Company.query.get(f_id)
                    if comp and comp.user_id == req_user_id:
                        allowed = True
                if req_role == 'student' and f_role == 'student':
                    # when student export, filename uses User.id
                    if int(req_user_id) == int(f_id):
                        allowed = True
                if allowed:
                    info = {'id': task_id, 'state': res.state, 'info': res.info}
                    return jsonify(info)
                break

    return jsonify({'msg': 'Not authorized to view this task status'}), 403


@tasks_bp.route('/download_export/<task_id>')
@jwt_required()
def download_export(task_id):
    identity = get_jwt_identity()
    req_user_id = identity.get('id') if isinstance(identity, dict) else identity
    req_role = identity.get('role') if isinstance(identity, dict) else None

    # admin can download any
    import os
    exports_dir = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), 'exports')
    for f in os.listdir(exports_dir):
        if task_id in f:
            # parse metadata from filename
            parts = f.split('_')
            if len(parts) >= 4:
                f_role = parts[1]
                f_id_part = parts[2]
                try:
                    f_id = int(f_id_part)
                except Exception:
                    f_id = f_id_part

                if req_role == 'admin':
                    return send_file(os.path.join(exports_dir, f), as_attachment=True)

                if req_role == 'company' and f_role == 'company':
                    comp = Company.query.get(f_id)
                    if comp and comp.user_id == req_user_id:
                        return send_file(os.path.join(exports_dir, f), as_attachment=True)

                if req_role == 'student' and f_role == 'student':
                    # student can download only their own export
                    if int(req_user_id) == int(f_id):
                        return send_file(os.path.join(exports_dir, f), as_attachment=True)

            # not authorized for this file
            return jsonify({'msg': 'Not authorized to download this export'}), 403

    return jsonify({'msg': 'Export not found'}), 404
