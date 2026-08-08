from datetime import datetime
from db import db

# Role constants
ROLE_ADMIN = 'admin'
ROLE_COMPANY = 'company'
ROLE_STUDENT = 'student'

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Company(db.Model):
    __tablename__ = 'company'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    hr_contact = db.Column(db.String(255))
    website = db.Column(db.String(255))
    approved = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='company_profile')

class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='student_profile')
    name = db.Column(db.String(255))
    branch = db.Column(db.String(50))
    cgpa = db.Column(db.Float)
    year = db.Column(db.Integer)
    resume_path = db.Column(db.String(1024))

class PlacementDrive(db.Model):
    __tablename__ = 'placement_drive'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    company = db.relationship('Company', backref='placement_drives')
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    eligibility = db.Column(db.String(1024))
    application_deadline = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='Pending')
    extra = db.Column(db.JSON, nullable=True)

class Application(db.Model):
    __tablename__ = 'application'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    student = db.relationship('Student', backref='applications')
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    drive = db.relationship('PlacementDrive', backref='applications')
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='Applied')
    extra = db.Column(db.JSON, nullable=True)

class Placement(db.Model):
    __tablename__ = 'placement'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    position = db.Column(db.String(255))
    salary = db.Column(db.String(100))
    joining_date = db.Column(db.DateTime)
