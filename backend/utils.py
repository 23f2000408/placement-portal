from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt


def role_required(role):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            user_role = claims.get('role')
            if user_role != role:
                return jsonify({'msg': 'forbidden - requires role: %s' % role}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def any_role_required(roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            user_role = claims.get('role')
            if user_role not in roles:
                return jsonify({'msg': 'forbidden - requires one of: %s' % ','.join(roles)}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
