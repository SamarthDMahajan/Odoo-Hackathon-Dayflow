from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dayflow2.db'
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    emp_id = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    check_in = db.Column(db.String(20), nullable=True)
    check_out = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default='Present')

class Leave(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.String(20), nullable=False)
    end_date = db.Column(db.String(20), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.String(50), nullable=False)

# Helper function to add audit logs easily
def log_action(user_name, action):
    new_log = AuditLog(
        user_name=user_name,
        action=action,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.session.add(new_log)
    db.session.commit()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        emp_id = request.form.get('emp_id')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please login.')
            return redirect(url_for('register'))

        new_user = User(name=name, emp_id=emp_id, email=email, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        
        log_action(name, f"Registered new account as {role}")
        flash('Registration successful! Please login.')
        return redirect(url_for('index'))
        
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if user and user.password == password:
        session['user_id'] = user.id
        session['role'] = user.role
        session['name'] = user.name
        
        log_action(user.name, "Logged into Dayflow HRMS")
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid email or password.')
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    role = session.get('role', 'Employee')
    today = datetime.now().strftime('%Y-%m-%d')
    
    total_employees = User.query.count()
    present_today = Attendance.query.filter_by(date=today).count()
    pending_leaves = Leave.query.filter_by(status='Pending').count()
    
    leaves = Leave.query.all() if role == 'Admin / HR' else Leave.query.filter_by(user_id=session['user_id']).all()
    users = User.query.all() if role == 'Admin / HR' else []
    
    return render_template('dashboard.html', 
                           name=session.get('name', 'User'), 
                           role=role, 
                           leaves=leaves,
                           users=users,
                           total_employees=total_employees,
                           present_today=present_today,
                           pending_leaves=pending_leaves)

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    action = request.form.get('action')
    today = datetime.now().strftime('%Y-%m-%d')
    
    att = Attendance.query.filter_by(user_id=session['user_id'], date=today).first()
    user_name = session.get('name', 'User')
    
    if action == 'check_in':
        if not att:
            new_att = Attendance(
                user_id=session['user_id'], 
                date=today, 
                check_in=datetime.now().strftime('%H:%M:%S'), 
                status='Present'
            )
            db.session.add(new_att)
            db.session.commit()
            log_action(user_name, "Checked in for daily attendance")
            flash('Checked in successfully!')
    elif action == 'check_out':
        if att:
            att.check_out = datetime.now().strftime('%H:%M:%S')
            db.session.commit()
            log_action(user_name, "Checked out of daily attendance")
            flash('Checked out successfully!')
            
    return redirect(url_for('dashboard'))

@app.route('/apply_leave', methods=['POST'])
def apply_leave():
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    leave_type = request.form.get('leave_type')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    reason = request.form.get('reason')
    
    new_leave = Leave(
        user_id=session['user_id'],
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason
    )
    db.session.add(new_leave)
    db.session.commit()
    
    log_action(session.get('name'), f"Applied for {leave_type} ({start_date} to {end_date})")
    flash('Leave application submitted successfully!')
    return redirect(url_for('dashboard'))

@app.route('/update_leave/<int:leave_id>/<status>')
def update_leave(leave_id, status):
    if 'user_id' not in session or session.get('role') != 'Admin / HR':
        return redirect(url_for('index'))
        
    leave = Leave.query.get_or_404(leave_id)
    leave.status = status
    db.session.commit()
    
    log_action(session.get('name'), f"Updated leave request #{leave_id} to {status}")
    flash(f'Leave request marked as {status}!')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    log_action(session.get('name', 'User'), "Logged out of system")
    session.clear()
    return redirect(url_for('index'))

@app.route('/export_attendance')
def export_attendance():
    if 'user_id' not in session or session.get('role') != 'Admin / HR':
        return redirect(url_for('index'))
        
    records = db.session.query(Attendance, User).join(User, Attendance.user_id == User.id).all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Employee ID', 'Name', 'Date', 'Check In', 'Check Out', 'Status'])
    
    for att, user in records:
        cw.writerow([user.emp_id, user.name, att.date, att.check_in, att.check_out, att.status])
        
    output = si.getvalue()
    log_action(session.get('name'), "Downloaded attendance CSV compliance report")
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=attendance_report.csv"}
    )

@app.route('/payroll')
def payroll():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    role = session.get('role', 'Employee')
    
    if role == 'Admin / HR':
        users = User.query.all()
        payroll_data = []
        for u in users:
            days_present = Attendance.query.filter_by(user_id=u.id, status='Present').count()
            total_salary = days_present * 100
            payroll_data.append({
                'emp_id': u.emp_id,
                'name': u.name,
                'role': u.role,
                'days_present': days_present,
                'salary': total_salary
            })
    else:
        u = User.query.get(session['user_id'])
        days_present = Attendance.query.filter_by(user_id=u.id, status='Present').count()
        total_salary = days_present * 100
        payroll_data = [{
            'emp_id': u.emp_id,
            'name': u.name,
            'role': u.role,
            'days_present': days_present,
            'salary': total_salary
        }]
        
    return render_template('payroll.html', payroll_data=payroll_data, name=session.get('name'), role=role)

@app.route('/audit_logs')
def audit_logs():
    if 'user_id' not in session or session.get('role') != 'Admin / HR':
        return redirect(url_for('dashboard'))
    
    logs = AuditLog.query.order_by(AuditLog.id.desc()).all()
    return render_template('audit_logs.html', logs=logs, name=session.get('name'), role=session.get('role'))

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    days_present = Attendance.query.filter_by(user_id=user.id, status='Present').count()
    total_leaves = Leave.query.filter_by(user_id=user.id).count()
    
    return render_template('profile.html', user=user, days_present=days_present, total_leaves=total_leaves, name=user.name, role=user.role)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)