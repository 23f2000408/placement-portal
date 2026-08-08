from flask import Blueprint, jsonify
from db import db
from sqlalchemy import inspect
from models import User, Company, Student, PlacementDrive, Application

status_bp = Blueprint('status', __name__)

@status_bp.route('/health', methods=['GET'])
def health():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    counts = {}
    try:
        counts['users'] = User.query.count()
    except Exception:
        counts['users'] = None
    try:
        counts['companies'] = Company.query.count()
    except Exception:
        counts['companies'] = None
    try:
        counts['students'] = Student.query.count()
    except Exception:
        counts['students'] = None
    try:
        counts['drives'] = PlacementDrive.query.count()
    except Exception:
        counts['drives'] = None
    try:
        counts['applications'] = Application.query.count()
    except Exception:
        counts['applications'] = None

    return jsonify({'tables': tables, 'counts': counts}), 200
