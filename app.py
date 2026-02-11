"""
SINCET College Digital Notice Board System
==========================================
Production-ready Flask application
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
from functools import wraps
import os, json, qrcode, base64, pandas as pd
from io import BytesIO
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sincet_noticeboard_secret_key_2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///sincet_noticeboard.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEPARTMENTS = {
    'CSE': {'name': 'Computer Science & Engineering', 'hod_email': 'csehodsincet@gmail.com'},
    'ECE': {'name': 'Electronics & Communication Engineering', 'hod_email': 'ecehodsincet@gmail.com'},
    'EEE': {'name': 'Electrical & Electronics Engineering', 'hod_email': 'eeehodsincet@gmail.com'},
    'IT': {'name': 'Information Technology', 'hod_email': 'ithodsincet@gmail.com'},
    'MECH': {'name': 'Mechanical Engineering', 'hod_email': 'mechhodsincet@gmail.com'},
    'CIVIL': {'name': 'Civil Engineering', 'hod_email': 'civilhodsincet@gmail.com'},
    'AIDS': {'name': 'AI & Data Science', 'hod_email': 'aidshodsincet@gmail.com'},
    'AIML': {'name': 'AI & Machine Learning', 'hod_email': 'aimlhodsincet@gmail.com'}
}

PRINCIPAL_EMAIL = os.environ.get('PRINCIPAL_EMAIL', 'principalsincet@gmail.com')
DEFAULT_PASSWORD = os.environ.get('DEFAULT_PASSWORD', 'sincet123')
YEARS = ['1st Year', '2nd Year', '3rd Year', '4th Year']
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'webm', 'ogg', 'wav'}

# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(20), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    department = db.Column(db.String(20), nullable=True)
    priority = db.Column(db.String(20), default='normal')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    attachment = db.Column(db.String(200), nullable=True)
    attachment_type = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    views = db.Column(db.Integer, default=0)
    display_duration = db.Column(db.Integer, default=10)
    for_all_departments = db.Column(db.Boolean, default=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    event_time = db.Column(db.String(20), nullable=True)
    venue = db.Column(db.String(200), nullable=True)
    department = db.Column(db.String(20), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    image = db.Column(db.String(200), nullable=True)
    display_duration = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(20), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    semester = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(200), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    register_number = db.Column(db.String(50), unique=True, nullable=False)
    department = db.Column(db.String(20), nullable=False)
    year = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class AttendanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)
    recorded_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student = db.relationship('Student', backref='attendance_records')

class DepartmentSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(20), unique=True, nullable=False)
    text_duration = db.Column(db.Integer, default=4)
    photo_duration = db.Column(db.Integer, default=5)
    video_duration = db.Column(db.Integer, default=30)
    total_working_days = db.Column(db.Integer, default=0)

class MediaContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(20), nullable=True)
    content_type = db.Column(db.String(20), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    title = db.Column(db.String(200), nullable=True)
    display_order = db.Column(db.Integer, default=0)
    display_duration = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') not in ['principal', 'hod']:
            flash('You do not have permission.', 'danger')
            return redirect(url_for('viewer'))
        return f(*args, **kwargs)
    return decorated_function

def get_department_from_email(email):
    for dept_code, dept_info in DEPARTMENTS.items():
        if dept_info['hod_email'].lower() == email.lower():
            return dept_code
    return None

def generate_qr_code(data, size=10):
    qr = qrcode.QRCode(version=1, box_size=size, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    if not filename: return None
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in {'png', 'jpg', 'jpeg', 'gif'}: return 'image'
    elif ext in {'mp4', 'webm', 'ogg'}: return 'video'
    elif ext in {'mp3', 'wav'}: return 'audio'
    elif ext == 'pdf': return 'pdf'
    return 'document'

def create_upload_folders():
    folders = ['static/uploads/notices', 'static/uploads/events', 'static/uploads/results',
               'static/uploads/media/images', 'static/uploads/media/videos',
               'static/uploads/college_ads', 'static/exports/attendance']
    for folder in folders:
        os.makedirs(folder, exist_ok=True)

def init_department_settings():
    for dept_code in DEPARTMENTS.keys():
        if not DepartmentSettings.query.filter_by(department=dept_code).first():
            db.session.add(DepartmentSettings(department=dept_code))
    db.session.commit()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        login_type = request.form.get('login_type', 'staff')

        if password != DEFAULT_PASSWORD:
            flash('Invalid password!', 'danger')
            return redirect(url_for('login'))

        if login_type == 'principal':
            if email != PRINCIPAL_EMAIL.lower():
                flash('Invalid principal email!', 'danger')
                return redirect(url_for('login'))
            role, department, name = 'principal', None, 'Principal'
        elif login_type == 'staff':
            department = get_department_from_email(email)
            if not department:
                flash('Invalid HOD email!', 'danger')
                return redirect(url_for('login'))
            role, name = 'hod', f'HOD - {DEPARTMENTS[department]["name"]}'
        else:
            role, department, name = 'general', None, 'Visitor'

        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, password=password, role=role, department=department, name=name)
            db.session.add(user)
            db.session.commit()

        session['user_id'], session['email'], session['role'] = user.id, user.email, role
        session['department'], session['name'] = department, name

        flash(f'Welcome, {name}!', 'success')
        return redirect(url_for('viewer') if role == 'general' else url_for('dashboard'))

    return render_template('login.html', login_type=request.args.get('type', 'staff'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@admin_required
def dashboard():
    role = session.get('role')
    department = session.get('department')
    selected_dept = request.args.get('dept', department if role == 'hod' else 'all')

    if role == 'principal':
        if selected_dept and selected_dept != 'all':
            notices = Notice.query.filter((Notice.department == selected_dept) | (Notice.for_all_departments == True), Notice.is_active == True).order_by(Notice.created_at.desc()).limit(10).all()
            events = Event.query.filter((Event.department == selected_dept) | (Event.department == None), Event.is_active == True).order_by(Event.event_date.desc()).limit(10).all()
        else:
            notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).limit(10).all()
            events = Event.query.filter_by(is_active=True).order_by(Event.event_date.desc()).limit(10).all()
        total_notices = Notice.query.filter_by(is_active=True).count()
        total_events = Event.query.filter_by(is_active=True).count()
    else:
        notices = Notice.query.filter((Notice.department == department) | (Notice.for_all_departments == True), Notice.is_active == True).order_by(Notice.created_at.desc()).limit(10).all()
        events = Event.query.filter((Event.department == department) | (Event.department == None), Event.is_active == True).order_by(Event.event_date.desc()).limit(10).all()
        total_notices = Notice.query.filter((Notice.department == department) | (Notice.for_all_departments == True), Notice.is_active == True).count()
        total_events = Event.query.filter((Event.department == department) | (Event.department == None), Event.is_active == True).count()
        selected_dept = department

    attendance_data = {}
    for year in YEARS:
        query_dept = selected_dept if selected_dept != 'all' else None
        students = Student.query.filter_by(department=query_dept, year=year, is_active=True).all() if query_dept else Student.query.filter_by(year=year, is_active=True).all()
        total_present = sum(AttendanceRecord.query.filter_by(student_id=s.id, status='present').count() for s in students)
        total_absent = sum(AttendanceRecord.query.filter_by(student_id=s.id, status='absent').count() for s in students)
        attendance_data[year] = {'present': total_present, 'absent': total_absent, 'total': total_present + total_absent}

    return render_template('dashboard.html', notices=notices, events=events, total_notices=total_notices, total_events=total_events,
                         attendance_data=json.dumps(attendance_data), departments=DEPARTMENTS, years=YEARS,
                         role=role, department=department, selected_dept=selected_dept)

@app.route('/viewer')
def viewer():
    notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).all()
    events = Event.query.filter_by(is_active=True).order_by(Event.event_date.asc()).all()
    results = Result.query.filter_by(is_active=True).order_by(Result.created_at.desc()).all()
    return render_template('viewer.html', notices=notices, events=events, results=results, departments=DEPARTMENTS)

@app.route('/notices')
@admin_required
def notices():
    role, department = session.get('role'), session.get('department')
    all_notices = Notice.query.order_by(Notice.created_at.desc()).all() if role == 'principal' else Notice.query.filter((Notice.department == department) | (Notice.for_all_departments == True)).order_by(Notice.created_at.desc()).all()
    return render_template('notices.html', notices=all_notices, departments=DEPARTMENTS)

@app.route('/notice/add', methods=['GET', 'POST'])
@admin_required
def add_notice():
    if request.method == 'POST':
        title, content = request.form.get('title'), request.form.get('content')
        department = request.form.get('department') or None
        priority = request.form.get('priority', 'normal')
        expires_at = request.form.get('expires_at')
        for_all = request.form.get('for_all_departments') == 'on'

        attachment, attachment_type = None, None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join('static/uploads/notices', filename))
                attachment, attachment_type = f'uploads/notices/{filename}', get_file_type(file.filename)

        display_duration = int(request.form.get('display_duration', 10))
        notice = Notice(title=title, content=content, department=department if not for_all else None,
                       priority=priority, created_by=session.get('user_id'),
                       expires_at=datetime.strptime(expires_at, '%Y-%m-%d') if expires_at else None,
                       attachment=attachment, attachment_type=attachment_type,
                       display_duration=display_duration,
                       for_all_departments=for_all or session.get('role') == 'principal')
        db.session.add(notice)
        db.session.commit()
        socketio.emit('content_update', {'type': 'notice', 'action': 'add', 'id': notice.id})
        flash('Notice added successfully!', 'success')
        return redirect(url_for('notices'))
    return render_template('add_notice.html', departments=DEPARTMENTS, role=session.get('role'))

@app.route('/notice/<int:id>')
@admin_required
def view_notice(id):
    notice = Notice.query.get_or_404(id)
    role, department = session.get('role'), session.get('department')
    if role != 'principal' and notice.department != department and notice.department != None:
        return render_template('error.html', message='Access denied'), 403
    return render_template('view_notice.html', notice=notice, departments=DEPARTMENTS)

@app.route('/notice/delete/<int:id>')
@admin_required
def delete_notice(id):
    notice = Notice.query.get_or_404(id)
    notice.is_active = False
    db.session.commit()
    socketio.emit('content_update', {'type': 'notice', 'action': 'delete', 'id': id})
    flash('Notice deleted successfully!', 'success')
    return redirect(url_for('notices'))

@app.route('/events')
@admin_required
def events():
    role, department = session.get('role'), session.get('department')
    all_events = Event.query.order_by(Event.event_date.desc()).all() if role == 'principal' else Event.query.filter((Event.department == department) | (Event.department == None)).order_by(Event.event_date.desc()).all()
    return render_template('events.html', events=all_events, departments=DEPARTMENTS)

@app.route('/event/add', methods=['GET', 'POST'])
@admin_required
def add_event():
    if request.method == 'POST':
        title, description = request.form.get('title'), request.form.get('description')
        event_date, event_time = request.form.get('event_date'), request.form.get('event_time')
        venue, department = request.form.get('venue'), request.form.get('department') or None

        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join('static/uploads/events', filename))
                image = f'uploads/events/{filename}'

        display_duration = int(request.form.get('display_duration', 10))
        event = Event(title=title, description=description, event_date=datetime.strptime(event_date, '%Y-%m-%d'),
                     event_time=event_time, venue=venue, department=department, created_by=session.get('user_id'), image=image, display_duration=display_duration)
        db.session.add(event)
        db.session.commit()
        socketio.emit('content_update', {'type': 'event', 'action': 'add', 'id': event.id})
        flash('Event added successfully!', 'success')
        return redirect(url_for('events'))
    return render_template('add_event.html', departments=DEPARTMENTS)

@app.route('/event/<int:id>')
@admin_required
def view_event(id):
    event = Event.query.get_or_404(id)
    role, department = session.get('role'), session.get('department')
    if role != 'principal' and event.department != department and event.department != None:
        return render_template('error.html', message='Access denied'), 403
    return render_template('view_event.html', event=event, departments=DEPARTMENTS)

@app.route('/event/delete/<int:id>')
@admin_required
def delete_event(id):
    event = Event.query.get_or_404(id)
    event.is_active = False
    db.session.commit()
    socketio.emit('content_update', {'type': 'event', 'action': 'delete', 'id': id})
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('events'))

@app.route('/results')
@admin_required
def results():
    role, department = session.get('role'), session.get('department')
    all_results = Result.query.order_by(Result.created_at.desc()).all() if role == 'principal' else Result.query.filter_by(department=department).order_by(Result.created_at.desc()).all()
    return render_template('results.html', results=all_results, departments=DEPARTMENTS)

@app.route('/result/add', methods=['GET', 'POST'])
@admin_required
def add_result():
    if request.method == 'POST':
        title, department = request.form.get('title'), request.form.get('department')
        year, semester = request.form.get('year'), request.form.get('semester')
        description = request.form.get('description')

        file_path = None
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join('static/uploads/results', filename))
                file_path = f'uploads/results/{filename}'

        result = Result(title=title, department=department, year=year, semester=semester, description=description, file_path=file_path, created_by=session.get('user_id'))
        db.session.add(result)
        db.session.commit()
        flash('Result added successfully!', 'success')
        return redirect(url_for('results'))

    role, dept = session.get('role'), session.get('department')
    return render_template('add_result.html', departments=DEPARTMENTS if role == 'principal' else {dept: DEPARTMENTS[dept]}, years=YEARS)

@app.route('/result/<int:id>')
@admin_required
def view_result(id):
    result = Result.query.get_or_404(id)
    role, department = session.get('role'), session.get('department')
    if role != 'principal' and result.department != department:
        return render_template('error.html', message='Access denied'), 403
    return render_template('view_result.html', result=result, departments=DEPARTMENTS)

@app.route('/students')
@admin_required
def students():
    role, department = session.get('role'), session.get('department')
    selected_dept = request.args.get('dept', department if role == 'hod' else None)
    selected_year = request.args.get('year', None)

    query = Student.query.filter_by(is_active=True)
    if role == 'hod': query = query.filter_by(department=department)
    elif selected_dept: query = query.filter_by(department=selected_dept)
    if selected_year: query = query.filter_by(year=selected_year)

    return render_template('students.html', students=query.order_by(Student.name).all(), departments=DEPARTMENTS, years=YEARS, selected_dept=selected_dept, selected_year=selected_year, role=role)

@app.route('/student/add', methods=['GET', 'POST'])
@admin_required
def add_student():
    if request.method == 'POST':
        name, register_number = request.form.get('name'), request.form.get('register_number')
        department, year = request.form.get('department'), request.form.get('year')

        if Student.query.filter_by(register_number=register_number).first():
            flash('Student with this register number already exists!', 'danger')
            return redirect(url_for('add_student'))

        db.session.add(Student(name=name, register_number=register_number, department=department, year=year))
        db.session.commit()
        flash('Student added successfully!', 'success')
        return redirect(url_for('students'))

    role, dept = session.get('role'), session.get('department')
    return render_template('add_student.html', departments=DEPARTMENTS if role == 'principal' else {dept: DEPARTMENTS[dept]}, years=YEARS)

@app.route('/student/bulk-add', methods=['GET', 'POST'])
@admin_required
def bulk_add_students():
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']
        if file and file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
            added = 0
            for _, row in df.iterrows():
                try:
                    reg_num = str(row.get('RegisterNumber', row.get('register_number', '')))
                    if reg_num and not Student.query.filter_by(register_number=reg_num).first():
                        db.session.add(Student(name=str(row.get('Name', row.get('name', ''))), register_number=reg_num,
                                              department=str(row.get('Department', row.get('department', ''))),
                                              year=str(row.get('Year', row.get('year', '')))))
                        added += 1
                except: continue
            db.session.commit()
            flash(f'{added} students added successfully!', 'success')
            return redirect(url_for('students'))
    return render_template('bulk_add_students.html')

@app.route('/attendance')
@admin_required
def attendance():
    role, department = session.get('role'), session.get('department')
    return render_template('attendance.html', departments=DEPARTMENTS, years=YEARS,
                         selected_dept=request.args.get('dept', department if role == 'hod' else None),
                         selected_year=request.args.get('year'), role=role)

@app.route('/attendance/mark', methods=['GET', 'POST'])
@admin_required
def mark_attendance():
    role, department = session.get('role'), session.get('department')

    if request.method == 'POST':
        date_str = request.form.get('date')
        dept = request.form.get('department')
        year = request.form.get('year')

        if not date_str or not date_str.strip():
            flash('Invalid date provided!', 'danger')
            return redirect(url_for('mark_attendance', dept=dept, year=year))
        if not dept or not year:
            flash('Department and year are required!', 'danger')
            return redirect(url_for('mark_attendance'))

        try:
            attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format!', 'danger')
            return redirect(url_for('mark_attendance', dept=dept, year=year))

        for student in Student.query.filter_by(department=dept, year=year, is_active=True).all():
            status = request.form.get(f'attendance_{student.id}', '').strip() or None
            if status in ['present', 'absent']:
                existing = AttendanceRecord.query.filter_by(student_id=student.id, date=attendance_date).first()
                if existing:
                    existing.status = status
                else:
                    db.session.add(AttendanceRecord(student_id=student.id, date=attendance_date, status=status, recorded_by=session.get('user_id')))

        db.session.commit()
        flash('Attendance marked successfully!', 'success')
        return redirect(url_for('attendance'))

    selected_dept = request.args.get('department', department if role == 'hod' else None)
    selected_year = request.args.get('year', '1st Year')
    today = datetime.now()
    selected_date = request.args.get('date', today.strftime('%Y-%m-%d'))

    students = []
    existing_attendance = {}
    if selected_dept and selected_year:
        try:
            attendance_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            students = Student.query.filter_by(department=selected_dept, year=selected_year, is_active=True).order_by(Student.name).all()
            for student in students:
                record = AttendanceRecord.query.filter_by(student_id=student.id, date=attendance_date).first()
                student.today_status = record.status if record else None
                existing_attendance[student.id] = record.status if record else None
        except ValueError:
            flash('Invalid date format!', 'danger')

    return render_template('mark_attendance.html', students=students,
                         existing_attendance=existing_attendance,
                         departments=DEPARTMENTS if role == 'principal' else {department: DEPARTMENTS[department]},
                         years=YEARS, selected_dept=selected_dept, selected_year=selected_year,
                         selected_date=selected_date, today=today)

@app.route('/attendance/view')
@admin_required
def view_attendance():
    role, department = session.get('role'), session.get('department')
    selected_dept = request.args.get('dept', department if role == 'hod' else None)
    selected_year = request.args.get('year', '1st Year')

    today = datetime.now().date()
    dates = [(today - timedelta(days=i)) for i in range(10)]
    dates.reverse()

    students = []
    attendance_data = {}
    if selected_dept and selected_year:
        students = Student.query.filter_by(department=selected_dept, year=selected_year, is_active=True).order_by(Student.name).all()
        for student in students:
            student_attendance = {}
            for date in dates:
                record = AttendanceRecord.query.filter_by(student_id=student.id, date=date).first()
                student_attendance[date.strftime('%Y-%m-%d')] = record.status if record else '-'

            student.attendance_data = student_attendance
            attendance_data[student.id] = {
                'dates': student_attendance,
                'present': AttendanceRecord.query.filter_by(student_id=student.id, status='present').count(),
                'absent': AttendanceRecord.query.filter_by(student_id=student.id, status='absent').count()
            }

            student.total_present = attendance_data[student.id]['present']
            student.total_absent = attendance_data[student.id]['absent']
            total_days = student.total_present + student.total_absent
            student.percentage = round((student.total_present / total_days * 100), 1) if total_days > 0 else 0

    return render_template('view_attendance.html', students=students, dates=dates,
                         attendance_data=attendance_data,
                         departments=DEPARTMENTS if role == 'principal' else {department: DEPARTMENTS[department]},
                         years=YEARS, selected_dept=selected_dept, selected_year=selected_year)

@app.route('/attendance/export')
@admin_required
def export_attendance():
    role, department = session.get('role'), session.get('department')
    selected_dept = request.args.get('dept', department if role == 'hod' else None)
    selected_year = request.args.get('year')

    if not selected_dept or not selected_year:
        flash('Please select department and year!', 'danger')
        return redirect(url_for('attendance'))

    students = Student.query.filter_by(department=selected_dept, year=selected_year, is_active=True).order_by(Student.name).all()
    today = datetime.now().date()
    dates = [(today - timedelta(days=i)) for i in range(9, -1, -1)]

    data = []
    for idx, student in enumerate(students, 1):
        row = {'S.No': idx, 'Name': student.name, 'Register Number': student.register_number}
        total_present, total_absent = 0, 0
        for date in dates:
            record = AttendanceRecord.query.filter_by(student_id=student.id, date=date).first()
            status = record.status if record else '-'
            row[date.strftime('%d/%m/%Y')] = 'P' if status == 'present' else ('A' if status == 'absent' else '-')
            if status == 'present': total_present += 1
            elif status == 'absent': total_absent += 1
        row['Present'], row['Absent'] = total_present, total_absent
        total_days = total_present + total_absent
        row['Overall Attendance %'] = f"{(total_present / total_days * 100):.1f}%" if total_days > 0 else "0%"
        data.append(row)

    filepath = os.path.join('static/exports/attendance', f"attendance_{selected_dept}_{selected_year.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
    pd.DataFrame(data).to_excel(filepath, index=False)
    return send_file(filepath, as_attachment=True)

@app.route('/attendance/add')
@admin_required
def add_attendance():
    return redirect(url_for('mark_attendance'))

@app.route('/settings/tv', methods=['GET', 'POST'])
@admin_required
def tv_settings():
    role, department = session.get('role'), session.get('department')
    if role != 'hod':
        flash('Only HODs can configure TV settings!', 'danger')
        return redirect(url_for('dashboard'))

    settings = DepartmentSettings.query.filter_by(department=department).first()
    if not settings:
        settings = DepartmentSettings(department=department)
        db.session.add(settings)
        db.session.commit()

    if request.method == 'POST':
        settings.text_duration = int(request.form.get('text_duration', 4))
        settings.photo_duration = int(request.form.get('photo_duration', 5))
        settings.video_duration = int(request.form.get('video_duration', 30))
        settings.total_working_days = int(request.form.get('total_working_days', 0))
        db.session.commit()
        socketio.emit('settings_update', {'department': department})
        flash('TV settings updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('tv_settings.html', settings=settings, department=department)

@app.route('/media/upload', methods=['GET', 'POST'])
@admin_required
def upload_media():
    role, department = session.get('role'), session.get('department')

    if request.method == 'POST' and 'file' in request.files:
        content_type = request.form.get('content_type', 'image')
        title = request.form.get('title', '')
        dept = request.form.get('department') if role == 'principal' else department
        file = request.files['file']

        if file and file.filename:
            filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            folder = 'static/uploads/media/images' if content_type == 'image' else 'static/uploads/media/videos'
            file.save(os.path.join(folder, filename))
            file_path = f'uploads/media/{"images" if content_type == "image" else "videos"}/{filename}'

            display_duration = int(request.form.get('display_duration', 10))
            db.session.add(MediaContent(department=dept, content_type=content_type, file_path=file_path, title=title, display_duration=display_duration))
            db.session.commit()
            socketio.emit('content_update', {'type': 'media', 'action': 'add'})
            flash('Media uploaded successfully!', 'success')
            return redirect(url_for('upload_media'))

    media_list = MediaContent.query.filter_by(is_active=True).order_by(MediaContent.created_at.desc()).all() if role == 'principal' else MediaContent.query.filter((MediaContent.department == department) | (MediaContent.department == None), MediaContent.is_active == True).order_by(MediaContent.created_at.desc()).all()
    return render_template('upload_media.html', media_list=media_list, departments=DEPARTMENTS, role=role, department=department)

@app.route('/media/delete/<int:id>')
@admin_required
def delete_media(id):
    media = MediaContent.query.get_or_404(id)
    media.is_active = False
    db.session.commit()
    socketio.emit('content_update', {'type': 'media', 'action': 'delete'})
    flash('Media deleted successfully!', 'success')
    return redirect(url_for('upload_media'))

@app.route('/tv')
def tv_display():
    return redirect(url_for('tv_department', dept='all'))

@app.route('/tv/<dept>')
def tv_department(dept):
    if dept not in DEPARTMENTS and dept != 'all':
        return redirect(url_for('tv_display'))

    settings = DepartmentSettings.query.filter_by(department=dept).first() if dept != 'all' else None
    text_duration = settings.text_duration if settings else 4
    photo_duration = settings.photo_duration if settings else 5
    video_duration = settings.video_duration if settings else 30

    if dept == 'all':
        notices_query = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.asc()).all()
        images_query = MediaContent.query.filter_by(content_type='image', is_active=True).order_by(MediaContent.created_at.asc()).all()
        videos_query = MediaContent.query.filter_by(content_type='video', is_active=True).order_by(MediaContent.created_at.asc()).all()
        events_query = Event.query.filter_by(is_active=True).order_by(Event.created_at.asc()).all()
    else:
        notices_query = Notice.query.filter((Notice.department == dept) | (Notice.for_all_departments == True), Notice.is_active == True).order_by(Notice.created_at.asc()).all()
        images_query = MediaContent.query.filter((MediaContent.department == dept) | (MediaContent.department == None), MediaContent.content_type == 'image', MediaContent.is_active == True).order_by(MediaContent.created_at.asc()).all()
        videos_query = MediaContent.query.filter((MediaContent.department == dept) | (MediaContent.department == None), MediaContent.content_type == 'video', MediaContent.is_active == True).order_by(MediaContent.created_at.asc()).all()
        events_query = Event.query.filter((Event.department == dept) | (Event.department == None), Event.is_active == True).order_by(Event.created_at.asc()).all()

    notices = [{
        'id': n.id, 'title': n.title, 'content': n.content, 'department': n.department,
        'priority': n.priority, 'attachment': n.attachment, 'attachment_type': n.attachment_type,
        'created_at': n.created_at.isoformat() if n.created_at else None,
        'expires_at': n.expires_at.isoformat() if n.expires_at else None,
        'views': n.views, 'display_duration': n.display_duration or 10,
        'for_all_departments': n.for_all_departments
    } for n in notices_query]

    images = [{
        'id': i.id, 'file_path': i.file_path, 'title': i.title, 'department': i.department,
        'display_order': i.display_order, 'display_duration': i.display_duration or 10,
        'created_at': i.created_at.isoformat() if i.created_at else None
    } for i in images_query]

    videos = [{
        'id': v.id, 'file_path': v.file_path, 'title': v.title, 'department': v.department,
        'display_order': v.display_order, 'display_duration': v.display_duration or 30,
        'created_at': v.created_at.isoformat() if v.created_at else None
    } for v in videos_query]

    events = [{
        'id': e.id, 'title': e.title, 'description': e.description,
        'event_date': e.event_date.isoformat() if e.event_date else None,
        'event_time': e.event_time, 'venue': e.venue, 'department': e.department,
        'image': e.image, 'display_duration': e.display_duration or 10,
        'created_at': e.created_at.isoformat() if e.created_at else None
    } for e in events_query]

    college_ads = [f'uploads/college_ads/{f}' for f in os.listdir('static/uploads/college_ads') if f.lower().endswith(('.mp4', '.webm', '.ogg'))] if os.path.exists('static/uploads/college_ads') else []

    if dept == 'all':
        dept_name = 'All Departments'
    else:
        dept_name = DEPARTMENTS.get(dept, {}).get('name', dept)

    return render_template('tv_department.html',
                         dept=dept, department=dept_name, dept_name=dept_name,
                         notices=notices, images=images, videos=videos, events=events,
                         college_ads=college_ads,
                         text_duration=text_duration, photo_duration=photo_duration,
                         video_duration=video_duration, settings=settings,
                         departments=DEPARTMENTS)

@app.route('/qr/notice/<int:id>')
def qr_notice(id):
    notice = Notice.query.get_or_404(id)
    notice.views += 1
    db.session.commit()
    return render_template('qr_notice.html', notice=notice)

@app.route('/qr/event/<int:id>')
def qr_event(id):
    return render_template('qr_event.html', event=Event.query.get_or_404(id), departments=DEPARTMENTS)

@app.route('/qr/result/<int:id>')
def qr_result(id):
    return render_template('qr_result.html', result=Result.query.get_or_404(id), departments=DEPARTMENTS)

@app.route('/qr/generate/<content_type>/<int:id>')
def generate_qr(content_type, id):
    url = request.host_url + f'qr/{content_type}/{id}'
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    buffer = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format='PNG')
    buffer.seek(0)
    return send_file(buffer, mimetype='image/png')

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------
@app.route('/api/notices')
def api_notices():
    dept = request.args.get('dept')
    notices = Notice.query.filter((Notice.department == dept) | (Notice.for_all_departments == True), Notice.is_active == True).order_by(Notice.created_at.desc()).all() if dept else Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).all()
    return jsonify([{'id': n.id, 'title': n.title, 'content': n.content, 'department': n.department, 'priority': n.priority, 'attachment': n.attachment, 'attachment_type': n.attachment_type, 'created_at': n.created_at.isoformat(), 'views': n.views} for n in notices])

@app.route('/api/events')
def api_events():
    return jsonify([{'id': e.id, 'title': e.title, 'description': e.description, 'event_date': e.event_date.isoformat(), 'event_time': e.event_time, 'venue': e.venue, 'department': e.department, 'image': e.image} for e in Event.query.filter_by(is_active=True).order_by(Event.event_date.asc()).all()])

@app.route('/api/media/<dept>')
def api_media(dept):
    if dept == 'all':
        images = MediaContent.query.filter_by(content_type='image', is_active=True).all()
        videos = MediaContent.query.filter_by(content_type='video', is_active=True).all()
    else:
        images = MediaContent.query.filter((MediaContent.department == dept) | (MediaContent.department == None), MediaContent.content_type == 'image', MediaContent.is_active == True).all()
        videos = MediaContent.query.filter((MediaContent.department == dept) | (MediaContent.department == None), MediaContent.content_type == 'video', MediaContent.is_active == True).all()
    return jsonify({'images': [{'id': i.id, 'path': i.file_path, 'title': i.title} for i in images], 'videos': [{'id': v.id, 'path': v.file_path, 'title': v.title} for v in videos]})

@app.route('/api/settings/<dept>')
def api_settings(dept):
    settings = DepartmentSettings.query.filter_by(department=dept).first()
    return jsonify({'text_duration': settings.text_duration, 'photo_duration': settings.photo_duration, 'video_duration': settings.video_duration, 'total_working_days': settings.total_working_days} if settings else {'text_duration': 4, 'photo_duration': 5, 'video_duration': 30, 'total_working_days': 0})

# ---------------------------------------------------------------------------
# SocketIO Events
# ---------------------------------------------------------------------------
@socketio.on('connect')
def handle_connect(): print('Client connected')

@socketio.on('disconnect')
def handle_disconnect(): print('Client disconnected')

@socketio.on('refresh_display')
def handle_refresh(): emit('refresh', broadcast=True)

# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e): return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e): return render_template('error.html', error='Server error'), 500

# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
create_upload_folders()

with app.app_context():
    db.create_all()
    init_department_settings()

if __name__ == '__main__':
    print("Starting SINCET Digital Notice Board...")
    print(f"PRINCIPAL: {PRINCIPAL_EMAIL} / {DEFAULT_PASSWORD}")
    print("HODs:", ", ".join([f"{d}: {i['hod_email']}" for d, i in DEPARTMENTS.items()]))
    print("TV: http://localhost:5000/tv | Dashboard: http://localhost:5000/dashboard\n")
    socketio.run(app, debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
