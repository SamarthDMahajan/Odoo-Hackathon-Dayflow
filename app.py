from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dayflow.db'
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
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid email or password.')
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('dashboard.html', name=session.get('name', 'User'), role=session.get('role', 'Employee'))

@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    action = request.form.get('action')
    today = datetime.now().strftime('%Y-%m-%d')
    
    att = Attendance.query.filter_by(user_id=session['user_id'], date=today).first()
    
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
    elif action == 'check_out':
        if att:
            att.check_out = datetime.now().strftime('%H:%M:%S')
            db.session.commit()
            
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)