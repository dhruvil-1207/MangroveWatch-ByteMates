import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, Report
import uuid

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report')
@login_required
def report():
    return render_template('report.html')

@app.route('/how-it-works')
def how_it_works():
    return render_template('how_it_works.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        organization = request.form.get('organization')
        user_type = request.form.get('user_type', 'community')
        phone = request.form.get('phone')
        location = request.form.get('location')
        
        # Validation
        if not all([username, email, password]):
            flash('Please fill in all required fields.', 'error')
            return render_template('register.html')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use another email.', 'error')
            return render_template('register.html')
        
        # Create new user
        user = User()
        user.username = username
        user.email = email
        user.full_name = full_name
        user.organization = organization
        user.user_type = user_type
        user.phone = phone
        user.location = location
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's reports
    user_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()
    
    # Get all reports if user is authority
    if current_user.user_type == 'authority':
        all_reports = Report.query.order_by(Report.created_at.desc()).limit(50).all()
    else:
        all_reports = []
    
    return render_template('dashboard.html', user_reports=user_reports, all_reports=all_reports)

@app.route('/submit-report', methods=['POST'])
@login_required
def submit_report():
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        incident_type = request.form.get('incident_type')
        severity = request.form.get('severity', 'medium')
        incident_date_str = request.form.get('incident_date')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        location_name = request.form.get('location_name')
        
        # Validation
        if not all([title, description, incident_type, incident_date_str]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('report'))
        
        # Parse incident date
        try:
            if not incident_date_str:
                flash('Incident date is required.', 'error')
                return redirect(url_for('report'))
            incident_date = datetime.strptime(incident_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('report'))
        
        # Handle file upload
        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                # Generate unique filename
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                photo_filename = f"{uuid.uuid4()}.{file_ext}"
                
                # Create uploads directory if it doesn't exist
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                # Save file
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
                file.save(file_path)
        
        # Create report
        report = Report()
        report.title = title
        report.description = description
        report.incident_type = incident_type
        report.severity = severity
        report.incident_date = incident_date
        report.latitude = float(latitude) if latitude else None
        report.longitude = float(longitude) if longitude else None
        report.location_name = location_name
        report.photo_filename = photo_filename
        report.user_id = current_user.id
        
        db.session.add(report)
        db.session.commit()
        
        flash('Report submitted successfully! Thank you for helping protect our mangroves.', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        app.logger.error(f"Error submitting report: {str(e)}")
        flash('An error occurred while submitting your report. Please try again.', 'error')
        return redirect(url_for('report'))

@app.route('/api/reports')
@login_required
def api_reports():
    """API endpoint to get reports data for maps and charts"""
    reports = Report.query.all()
    reports_data = []
    
    for report in reports:
        reports_data.append({
            'id': report.id,
            'title': report.title,
            'incident_type': report.incident_type,
            'severity': report.severity,
            'status': report.status,
            'latitude': report.latitude,
            'longitude': report.longitude,
            'location_name': report.location_name,
            'created_at': report.created_at.isoformat(),
            'reporter': report.reporter.username if report.reporter else 'Unknown'
        })
    
    return jsonify(reports_data)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
