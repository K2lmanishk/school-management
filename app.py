# ============================================
# STUDENT MANAGEMENT SYSTEM - COMPLETE APP.PY
# All Features Working + All Fixes
# ============================================

# 1. IMPORTS
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session, send_file, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Student, Faculty, Course, Subject, Enrollment, Attendance, Marks, Fee, Notice, FacultyAssignment, Timetable, Notification
from config import Config
from datetime import datetime, timedelta
import json
import os
import qrcode
import io

# 2. APP INITIALIZATION
app = Flask(__name__)
app.config.from_object(Config)

# 3. CONFIGURATION & HELPER FUNCTIONS
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_sms(to_phone, message):
    """Send SMS via Twilio"""
    try:
        from twilio.rest import Client
        account_sid = app.config.get('TWILIO_ACCOUNT_SID')
        auth_token = app.config.get('TWILIO_AUTH_TOKEN')
        from_number = app.config.get('TWILIO_PHONE_NUMBER')
        
        if not account_sid or not auth_token or not from_number:
            print("Twilio credentials not configured!")
            return False, "Twilio credentials not configured"
        
        client = Client(account_sid, auth_token)
        msg = client.messages.create(body=message, from_=from_number, to=to_phone)
        print(f"SMS sent! SID: {msg.sid}")
        return True, msg.sid
    except Exception as e:
        print(f"SMS Error: {str(e)}")
        return False, str(e)

# 4. DATABASE & LOGIN MANAGER
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow(), 'today': datetime.utcnow().date()}

# ============================================
# 5. AUTHENTICATION ROUTES
# ============================================

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            session['user_role'] = user.role
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'faculty':
                return redirect(url_for('faculty_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('login'))

# ============================================
# 6. ADMIN ROUTES
# ============================================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    total_students = Student.query.count()
    total_faculty = Faculty.query.count()
    total_courses = Course.query.count()
    recent_notices = Notice.query.order_by(Notice.created_at.desc()).limit(5).all()
    return render_template('admin_dashboard.html',
                           total_students=total_students,
                           total_faculty=total_faculty,
                           total_courses=total_courses,
                           notices=recent_notices)

@app.route('/admin/users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    users = User.query.all()
    courses = Course.query.all()
    return render_template('manage_users.html', users=users, courses=courses)

@app.route('/admin/user/add', methods=['POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.form
    
    if User.query.filter_by(username=data['username']).first():
        flash(f'Username "{data["username"]}" already exists!', 'danger')
        return redirect(url_for('manage_users'))
    
    if User.query.filter_by(email=data['email']).first():
        flash(f'Email "{data["email"]}" already exists!', 'danger')
        return redirect(url_for('manage_users'))
    
    if data['role'] == 'student' and data.get('roll_no'):
        if Student.query.filter_by(roll_no=data['roll_no']).first():
            flash(f'Roll number "{data["roll_no"]}" already exists!', 'danger')
            return redirect(url_for('manage_users'))
    
    try:
        hashed_pw = generate_password_hash(data['password'])
        user = User(
            username=data['username'],
            email=data['email'],
            password_hash=hashed_pw,
            role=data['role'],
            full_name=data['full_name']
        )
        db.session.add(user)
        db.session.flush()
        
        if data['role'] == 'student':
            student = Student(
                user_id=user.id,
                roll_no=data.get('roll_no', ''),
                course_id=data.get('course_id') if data.get('course_id') else None,
                semester=data.get('semester') if data.get('semester') else None,
                dob=datetime.strptime(data['dob'], '%Y-%m-%d') if data.get('dob') else None,
                phone=data.get('phone', ''),
                address=data.get('address', ''),
                parent_contact=data.get('parent_contact', '')
            )
            db.session.add(student)
        elif data['role'] == 'faculty':
            faculty = Faculty(
                user_id=user.id,
                department=data.get('department', ''),
                designation=data.get('designation', ''),
                qualification=data.get('qualification', ''),
                joining_date=datetime.strptime(data['joining_date'], '%Y-%m-%d') if data.get('joining_date') else None
            )
            db.session.add(faculty)
        
        db.session.commit()
        flash('User added successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding user: {str(e)}', 'danger')
    
    return redirect(url_for('manage_users'))

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    user = User.query.get(user_id)
    if user:
        if user.role == 'student' and user.student_profile:
            db.session.delete(user.student_profile)
        elif user.role == 'faculty' and user.faculty_profile:
            db.session.delete(user.faculty_profile)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User deleted'})
    return jsonify({'success': False, 'message': 'User not found'})

@app.route('/admin/courses')
@login_required
def manage_courses():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    courses = Course.query.all()
    return render_template('manage_courses.html', courses=courses)

@app.route('/admin/course/add', methods=['POST'])
@login_required
def add_course():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if Course.query.filter_by(code=request.form['code']).first():
        flash(f'Course code "{request.form["code"]}" already exists!', 'danger')
        return redirect(url_for('manage_courses'))
    
    course = Course(
        name=request.form['name'],
        code=request.form['code'],
        duration_years=request.form['duration_years'],
        total_semesters=request.form['total_semesters']
    )
    db.session.add(course)
    db.session.commit()
    flash('Course added successfully', 'success')
    return redirect(url_for('manage_courses'))

@app.route('/admin/course/delete/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    course = Course.query.get(course_id)
    if course:
        db.session.delete(course)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Course deleted'})
    return jsonify({'success': False, 'message': 'Course not found'})

@app.route('/admin/subjects')
@login_required
def manage_subjects():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    subjects = Subject.query.all()
    courses = Course.query.all()
    return render_template('manage_subjects.html', subjects=subjects, courses=courses)

@app.route('/admin/subject/add', methods=['POST'])
@login_required
def add_subject():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if Subject.query.filter_by(code=request.form['code']).first():
        flash(f'Subject code "{request.form["code"]}" already exists!', 'danger')
        return redirect(url_for('manage_subjects'))
    
    subject = Subject(
        course_id=request.form['course_id'],
        semester=request.form['semester'],
        name=request.form['name'],
        code=request.form['code'],
        credits=request.form['credits'],
        type=request.form['type']
    )
    db.session.add(subject)
    db.session.commit()
    flash('Subject added successfully', 'success')
    return redirect(url_for('manage_subjects'))

@app.route('/admin/assign_faculty', methods=['GET', 'POST'])
@login_required
def assign_faculty():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        assignment = FacultyAssignment(
            faculty_id=request.form['faculty_id'],
            subject_id=request.form['subject_id'],
            academic_year=request.form['academic_year']
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Faculty assigned successfully', 'success')
        return redirect(url_for('assign_faculty'))
    faculties = Faculty.query.all()
    subjects = Subject.query.all()
    assignments = FacultyAssignment.query.all()
    return render_template('assign_faculty.html', faculties=faculties, subjects=subjects, assignments=assignments)

@app.route('/admin/notices', methods=['GET', 'POST'])
@login_required
def manage_notices():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        notice = Notice(
            title=request.form['title'],
            content=request.form['content'],
            audience=request.form['audience'],
            created_by=current_user.id
        )
        db.session.add(notice)
        db.session.commit()
        flash('Notice posted successfully', 'success')
        return redirect(url_for('manage_notices'))
    notices = Notice.query.order_by(Notice.created_at.desc()).all()
    return render_template('manage_notices.html', notices=notices)

@app.route('/admin/notice/delete/<int:notice_id>', methods=['POST'])
@login_required
def delete_notice(notice_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    notice = Notice.query.get(notice_id)
    if notice:
        db.session.delete(notice)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Notice deleted'})
    return jsonify({'success': False, 'message': 'Notice not found'})

# ============================================
# 7. FACULTY ROUTES
# ============================================

@app.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    if current_user.role != 'faculty':
        return redirect(url_for('login'))
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all() if faculty else []
    return render_template('faculty_dashboard.html', faculty=faculty, assignments=assignments)

@app.route('/faculty/attendance', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if current_user.role != 'faculty':
        return redirect(url_for('login'))
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all() if faculty else []
    
    if request.method == 'POST':
        subject_id = request.form['subject_id']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        subject = Subject.query.get(subject_id)
        students = Student.query.filter_by(course_id=subject.course_id, semester=subject.semester).all()
        
        for student in students:
            status = request.form.get('status_' + str(student.id), 'Absent')
            attendance = Attendance.query.filter_by(student_id=student.id, subject_id=subject_id, date=date).first()
            if not attendance:
                attendance = Attendance(student_id=student.id, subject_id=subject_id, date=date, status=status)
                db.session.add(attendance)
        db.session.commit()
        flash('Attendance marked successfully', 'success')
        return redirect(url_for('mark_attendance'))
    
    return render_template('attendance.html', assignments=assignments, today=datetime.utcnow().date())

@app.route('/faculty/marks', methods=['GET', 'POST'])
@login_required
def enter_marks():
    if current_user.role != 'faculty':
        return redirect(url_for('login'))
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    assignments = FacultyAssignment.query.filter_by(faculty_id=faculty.id).all() if faculty else []
    
    if request.method == 'POST':
        subject_id = request.form['subject_id']
        exam_type = request.form['exam_type']
        max_marks = int(request.form['max_marks'])
        subject = Subject.query.get(subject_id)
        students = Student.query.filter_by(course_id=subject.course_id, semester=subject.semester).all()
        
        for student in students:
            obtained = request.form.get('marks_' + str(student.id))
            if obtained:
                marks = Marks.query.filter_by(student_id=student.id, subject_id=subject_id, exam_type=exam_type).first()
                if not marks:
                    marks = Marks(student_id=student.id, subject_id=subject_id, exam_type=exam_type, max_marks=max_marks, obtained_marks=float(obtained))
                    db.session.add(marks)
                else:
                    marks.obtained_marks = float(obtained)
        db.session.commit()
        flash('Marks saved successfully', 'success')
        return redirect(url_for('enter_marks'))
    
    return render_template('marks_entry.html', assignments=assignments)

# ============================================
# 8. STUDENT ROUTES
# ============================================

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    attendance_percent = 0
    present = 0
    total_classes = 0
    recent_marks = []
    fee = None
    notices = []
    
    if student:
        attendance_records = Attendance.query.filter_by(student_id=student.id).all()
        total_classes = len(attendance_records)
        present = sum(1 for a in attendance_records if a.status == 'Present')
        attendance_percent = (present / total_classes * 100) if total_classes > 0 else 0
        
        recent_marks = Marks.query.filter_by(student_id=student.id).order_by(Marks.id.desc()).limit(5).all()
        fee = Fee.query.filter_by(student_id=student.id).order_by(Fee.due_date.desc()).first()
        notices = Notice.query.filter(Notice.audience.in_(['all', 'students'])).order_by(Notice.created_at.desc()).limit(5).all()
    
    return render_template('student_dashboard.html',
                           student=student,
                           attendance_percent=attendance_percent,
                           present=present,
                           total_classes=total_classes,
                           recent_marks=recent_marks,
                           fee=fee,
                           notices=notices)

@app.route('/student/attendance')
@login_required
def view_attendance():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    student = Student.query.filter_by(user_id=current_user.id).first()
    attendance = []
    if student:
        attendance = db.session.query(Attendance, Subject).join(Subject).filter(Attendance.student_id == student.id).all()
    return render_template('student_attendance.html', attendance=attendance)

@app.route('/student/marks')
@login_required
def view_marks():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    student = Student.query.filter_by(user_id=current_user.id).first()
    marks = []
    if student:
        marks = db.session.query(Marks, Subject).join(Subject).filter(Marks.student_id == student.id).all()
    return render_template('student_marks.html', marks=marks)

@app.route('/student/fees')
@login_required
def view_fees():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    student = Student.query.filter_by(user_id=current_user.id).first()
    fees = []
    if student:
        fees = Fee.query.filter_by(student_id=student.id).all()
    return render_template('student_fees.html', fees=fees)

# ============================================
# 9. QR CODE & ID CARD ROUTES
# ============================================

@app.route('/student/id-card')
@login_required
def student_id_card():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    student = Student.query.filter_by(user_id=current_user.id).first()
    return render_template('student_id_card.html', student=student)

@app.route('/student/qrcode/<roll_no>')
@login_required
def generate_qr(roll_no):
    data = f"{roll_no}|{url_for('mark_attendance', _external=True)}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

# ============================================
# 10. TIMETABLE ROUTES
# ============================================

@app.route('/admin/timetable')
@login_required
def manage_timetable():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    courses = Course.query.all()
    faculties = Faculty.query.all()
    subjects = Subject.query.all()
    timetables = Timetable.query.all()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    time_slots = ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00']
    return render_template('manage_timetable.html', courses=courses, faculties=faculties, subjects=subjects, timetables=timetables, days=days, time_slots=time_slots)

@app.route('/admin/timetable/add', methods=['POST'])
@login_required
def add_timetable():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    timetable = Timetable(
        course_id=request.form.get('course_id'),
        semester=request.form.get('semester'),
        day=request.form.get('day'),
        time_slot=request.form.get('time_slot'),
        subject_id=request.form.get('subject_id'),
        faculty_id=request.form.get('faculty_id'),
        room_no=request.form.get('room_no')
    )
    db.session.add(timetable)
    db.session.commit()
    flash('Timetable entry added!', 'success')
    return redirect(url_for('manage_timetable'))

@app.route('/admin/timetable/delete/<int:timetable_id>', methods=['POST'])
@login_required
def delete_timetable(timetable_id):
    if current_user.role != 'admin':
        return jsonify({'success': False}), 403
    timetable = Timetable.query.get(timetable_id)
    if timetable:
        db.session.delete(timetable)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/faculty/timetable')
@login_required
def faculty_timetable():
    if current_user.role != 'faculty':
        return redirect(url_for('login'))
    faculty = Faculty.query.filter_by(user_id=current_user.id).first()
    timetables = Timetable.query.filter_by(faculty_id=faculty.id).all() if faculty else []
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    time_slots = ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00']
    return render_template('faculty_timetable.html', timetables=timetables, days=days, time_slots=time_slots)

@app.route('/student/timetable')
@login_required
def student_timetable():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    student = Student.query.filter_by(user_id=current_user.id).first()
    timetables = Timetable.query.filter_by(course_id=student.course_id, semester=student.semester).all() if student else []
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    time_slots = ['09:00-10:00', '10:00-11:00', '11:00-12:00', '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00']
    return render_template('student_timetable.html', timetables=timetables, days=days, time_slots=time_slots)

# ============================================
# 11. NOTIFICATION ROUTES
# ============================================

@app.route('/admin/notifications-page')
@login_required
def manage_notifications_page():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    sent_notifications = Notification.query.filter_by(created_by=current_user.id).order_by(Notification.created_at.desc()).all()
    students = User.query.filter_by(role='student').all()
    faculty = User.query.filter_by(role='faculty').all()
    return render_template('manage_notifications.html', sent_notifications=sent_notifications, students=students, faculty=faculty)

@app.route('/admin/notification/send', methods=['POST'])
@login_required
def send_notification():
    if current_user.role != 'admin':
        return jsonify({'success': False}), 403
    
    notification = Notification(
        title=request.form.get('title'),
        message=request.form.get('message'),
        notification_type=request.form.get('notification_type', 'general'),
        audience=request.form.get('audience'),
        specific_user_id=request.form.get('specific_user_id') or None,
        created_by=current_user.id,
        expiry_date=datetime.strptime(request.form.get('expiry_date'), '%Y-%m-%d').date() if request.form.get('expiry_date') else None
    )
    db.session.add(notification)
    db.session.commit()
    flash('Notification sent!', 'success')
    return redirect(url_for('manage_notifications_page'))

@app.route('/admin/notification/delete/<int:notification_id>', methods=['POST'])
@login_required
def delete_notification(notification_id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    notification = Notification.query.get(notification_id)
    if notification and notification.created_by == current_user.id:
        db.session.delete(notification)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Notification deleted'})
    
    return jsonify({'success': False, 'message': 'Notification not found'})

@app.route('/api/notifications/unread')
@login_required
def get_unread_notifications():
    notifications = Notification.query.filter(
        ((Notification.audience == 'all') | 
         (Notification.audience == current_user.role) |
         (Notification.specific_user_id == current_user.id)) &
        (Notification.is_read == False)
    ).order_by(Notification.created_at.desc()).limit(10).all()
    
    return jsonify([{
        'id': n.id, 'title': n.title,
        'message': n.message[:100] + '...' if len(n.message) > 100 else n.message,
        'type': n.notification_type,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
        'time_ago': 'just now'
    } for n in notifications])

@app.route('/api/notification/mark-read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get(notification_id)
    if notification:
        notification.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/notification/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter(
        ((Notification.audience == 'all') | 
         (Notification.audience == current_user.role) |
         (Notification.specific_user_id == current_user.id))
    ).update({Notification.is_read: True})
    db.session.commit()
    return jsonify({'success': True})

# ============================================
# 12. SMS ROUTES
# ============================================

@app.route('/admin/send-sms')
@login_required
def send_sms_page():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    return render_template('send_sms.html')

@app.route('/admin/bulk-sms', methods=['POST'])
@login_required
def bulk_sms():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    audience = request.form.get('audience')
    message = request.form.get('message')
    
    if audience == 'all_students':
        students = Student.query.all()
    elif audience == 'due_fees':
        students = db.session.query(Student).join(Fee).filter(Fee.status != 'Paid').all()
    else:
        students = []
    
    success_count = 0
    for student in students:
        if student.phone:
            success, _ = send_sms(student.phone, message)
            if success:
                success_count += 1
    
    flash(f'SMS sent to {success_count} students!', 'success' if success_count > 0 else 'info')
    return redirect(url_for('send_sms_page'))

@app.route('/admin/send-fee-reminder/<int:student_id>')
@login_required
def send_fee_reminder(student_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    student = Student.query.get(student_id)
    if student and student.phone:
        fee = Fee.query.filter_by(student_id=student_id).filter(Fee.status != 'Paid').first()
        if fee:
            due = fee.amount - fee.paid_amount
            message = f"Dear {student.user.full_name}, your fee of Rs.{due:.2f} is pending. Due date: {fee.due_date}. - College Admin"
            success, sid = send_sms(student.phone, message)
            flash('SMS sent!' if success else f'Failed: {sid}', 'success' if success else 'danger')
    return redirect(url_for('admin_manage_fees'))

# ============================================
# 13. ADMIN FEE MANAGEMENT
# ============================================

@app.route('/admin/manage-fees')
@login_required
def admin_manage_fees():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    students = Student.query.all()
    fee_data = []
    total_fees = total_paid = pending_count = 0
    
    for student in students:
        fee = Fee.query.filter_by(student_id=student.id).order_by(Fee.due_date.desc()).first()
        if fee:
            fee_data.append({'student': student, 'fee': fee})
            total_fees += fee.amount
            total_paid += fee.paid_amount
            if fee.status != 'Paid':
                pending_count += 1
    
    total_due = total_fees - total_paid
    default_message = "Dear Student, your college fee is pending. Please pay at the earliest. - College Admin"
    
    return render_template('admin_fees.html', fee_data=fee_data, total_fees=total_fees, total_paid=total_paid, total_due=total_due, pending_count=pending_count, default_message=default_message)

@app.route('/admin/record-payment', methods=['POST'])
@login_required
def record_payment():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    fee_id = request.form.get('fee_id')
    payment_amount = float(request.form.get('payment_amount', 0))
    
    fee = Fee.query.get(fee_id)
    if fee:
        fee.paid_amount += payment_amount
        fee.status = 'Paid' if fee.paid_amount >= fee.amount else 'Partial'
        fee.payment_date = datetime.utcnow()
        db.session.commit()
        flash('Payment recorded!', 'success')
    return redirect(url_for('admin_manage_fees'))

# ============================================
# 14. PROFILE ROUTES
# ============================================

@app.route('/profile')
@login_required
def profile():
    user = current_user
    student = Student.query.filter_by(user_id=user.id).first() if user.role == 'student' else None
    faculty = Faculty.query.filter_by(user_id=user.id).first() if user.role == 'faculty' else None
    return render_template('profile.html', user=user, student=student, faculty=faculty)

@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    user = current_user
    data = request.form
    user.full_name = data.get('full_name', user.full_name)
    
    if user.role == 'student':
        student = Student.query.filter_by(user_id=user.id).first()
        if student:
            student.phone = data.get('phone', student.phone)
            student.address = data.get('address', student.address)
            student.parent_contact = data.get('parent_contact', student.parent_contact)
    elif user.role == 'faculty':
        faculty = Faculty.query.filter_by(user_id=user.id).first()
        if faculty:
            faculty.department = data.get('department', faculty.department)
            faculty.designation = data.get('designation', faculty.designation)
            faculty.qualification = data.get('qualification', faculty.qualification)
    
    db.session.commit()
    flash('Profile updated!', 'success')
    return redirect(url_for('profile'))

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Current password is incorrect!', 'danger')
    elif new_password != confirm_password:
        flash('Passwords do not match!', 'danger')
    elif len(new_password) < 6:
        flash('Password must be at least 6 characters!', 'danger')
    else:
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash('Password changed!', 'success')
    
    return redirect(url_for('profile'))

# ============================================
# 15. PROFILE PHOTO UPLOAD
# ============================================

@app.route('/upload_profile_pic', methods=['POST'])
@login_required
def upload_profile_pic():
    if 'profile_pic' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('profile'))
    
    file = request.files['profile_pic']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('profile'))
    
    if file and allowed_file(file.filename):
        try:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = secure_filename(f"user_{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{ext}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            if current_user.profile_pic and current_user.profile_pic != 'default.png':
                old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_pic)
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)
            
            current_user.profile_pic = filename
            db.session.commit()
            flash('Profile picture updated!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    else:
        flash('Invalid file type. Allowed: png, jpg, jpeg, gif, webp', 'danger')
    
    return redirect(url_for('profile'))

@app.route('/delete_profile_pic', methods=['POST'])
@login_required
def delete_profile_pic():
    if current_user.profile_pic and current_user.profile_pic != 'default.png':
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], current_user.profile_pic)
        if os.path.exists(filepath):
            os.remove(filepath)
        current_user.profile_pic = 'default.png'
        db.session.commit()
        flash('Profile picture removed', 'success')
    return redirect(url_for('profile'))

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============================================
# 16. API ENDPOINTS
# ============================================

@app.route('/api/get_students_by_subject/<int:subject_id>')
@login_required
def get_students_by_subject(subject_id):
    subject = Subject.query.get(subject_id)
    if not subject:
        return jsonify([])
    students = Student.query.filter_by(course_id=subject.course_id, semester=subject.semester).all()
    return jsonify([{'id': s.id, 'roll_no': s.roll_no, 'name': s.user.full_name} for s in students])

# ============================================
# 17. MAIN - APPLICATION ENTRY POINT
# ============================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@college.edu', password_hash=generate_password_hash('admin123'), role='admin', full_name='Administrator')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin created: admin / admin123")
        
        if Course.query.count() == 0:
            db.session.add_all([Course(name='Computer Science', code='CS', duration_years=4, total_semesters=8), Course(name='Information Technology', code='IT', duration_years=4, total_semesters=8)])
            db.session.commit()
            print("✅ Demo courses created!")
        
        if not User.query.filter_by(username='faculty1').first():
            faculty_user = User(username='faculty1', email='faculty1@college.edu', password_hash=generate_password_hash('pass123'), role='faculty', full_name='Dr. John Smith')
            db.session.add(faculty_user)
            db.session.commit()
            db.session.add(Faculty(user_id=faculty_user.id, department='Computer Science', designation='Professor', qualification='Ph.D.', joining_date=datetime.utcnow().date()))
            db.session.commit()
            print("✅ Demo faculty created: faculty1 / pass123")
        
        if not User.query.filter_by(username='student1').first():
            student_user = User(username='student1', email='student1@college.edu', password_hash=generate_password_hash('pass123'), role='student', full_name='Alice Johnson')
            db.session.add(student_user)
            db.session.commit()
            student = Student(user_id=student_user.id, roll_no='CS2024001', course_id=1, semester=1, dob=datetime(2005,5,15).date(), phone='+919876543210', address='123 College Street')
            db.session.add(student)
            db.session.commit()
            db.session.add(Fee(student_id=student.id, amount=50000, due_date=datetime.utcnow().date()+timedelta(days=30), paid_amount=25000, status='Partial'))
            db.session.commit()
            print("✅ Demo student created: student1 / pass123")
    
    app.run(debug=True)