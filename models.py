from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)
    full_name = db.Column(db.String(100))
    profile_pic = db.Column(db.String(200), default='default.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    student_profile = db.relationship('Student', backref='user', uselist=False)
    faculty_profile = db.relationship('Faculty', backref='user', uselist=False)
    sent_notifications = db.relationship('Notification', foreign_keys='Notification.created_by', backref='creator', lazy=True)
    personal_notifications = db.relationship('Notification', foreign_keys='Notification.specific_user_id', backref='specific_user', lazy=True)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    roll_no = db.Column(db.String(20), unique=True, nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    class_name = db.Column(db.String(50))  # Class 1 to Class 12
    dob = db.Column(db.Date)
    phone = db.Column(db.String(15))
    address = db.Column(db.Text)
    parent_contact = db.Column(db.String(15))
    
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)
    attendance_records = db.relationship('Attendance', backref='student', lazy=True)
    marks = db.relationship('Marks', backref='student', lazy=True)
    fee_records = db.relationship('Fee', backref='student', lazy=True)

class Faculty(db.Model):
    __tablename__ = 'faculty'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    department = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    qualification = db.Column(db.String(200))
    joining_date = db.Column(db.Date)
    
    assignments = db.relationship('FacultyAssignment', backref='faculty', lazy=True)
    timetable_entries = db.relationship('Timetable', backref='faculty', lazy=True)

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    description = db.Column(db.Text)
    
    subjects = db.relationship('Subject', backref='course', lazy=True)
    students = db.relationship('Student', backref='course', lazy=True)
    timetable_entries = db.relationship('Timetable', backref='course', lazy=True)

class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    class_name = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True)
    credits = db.Column(db.Integer)
    type = db.Column(db.String(20))
    
    assignments = db.relationship('FacultyAssignment', backref='subject', lazy=True)
    attendance = db.relationship('Attendance', backref='subject', lazy=True)
    marks = db.relationship('Marks', backref='subject', lazy=True)
    timetable_entries = db.relationship('Timetable', backref='subject', lazy=True)

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    academic_year = db.Column(db.String(20))
    enrollment_date = db.Column(db.Date, default=datetime.utcnow)

class FacultyAssignment(db.Model):
    __tablename__ = 'faculty_assignments'
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    academic_year = db.Column(db.String(20))

class Timetable(db.Model):
    __tablename__ = 'timetable'
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(20))
    time_slot = db.Column(db.String(50))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'))
    room_no = db.Column(db.String(20))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    class_name = db.Column(db.String(50))

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    date = db.Column(db.Date, default=datetime.utcnow)
    status = db.Column(db.String(10))

class Marks(db.Model):
    __tablename__ = 'marks'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    exam_type = db.Column(db.String(50))
    max_marks = db.Column(db.Integer)
    obtained_marks = db.Column(db.Float)

class Fee(db.Model):
    __tablename__ = 'fees'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    amount = db.Column(db.Float)
    due_date = db.Column(db.Date)
    paid_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Pending')
    transaction_id = db.Column(db.String(100))
    payment_date = db.Column(db.DateTime)

class Notice(db.Model):
    __tablename__ = 'notices'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    audience = db.Column(db.String(20))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='general')
    audience = db.Column(db.String(20), nullable=False)
    specific_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    expiry_date = db.Column(db.Date, nullable=True)