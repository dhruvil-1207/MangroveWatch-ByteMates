import os
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, Report
import uuid
import re
import asyncio
import json


def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route("/dashboard")
def ai_dashboard():
    return render_template("dashboard.html")


# Temporarily bypass login required for testing
@app.route('/report')
def report():
    return render_template('report.html')


# Temporarily bypass login required for testing
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

        if not all([username, email, password]):
            flash('Please fill in all required fields.', 'error')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.', 'error')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use another email.', 'error')
            return render_template('register.html')

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
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


# Updated /dashboard route to show recent and validated reports separately
@app.route('/dashboard')
def dashboard():
    # Mock user for testing: set appropriate user id and type
    class MockUser:
        id = 1
        user_type = 'authority'

    global current_user
    current_user = MockUser()

    # Fetch the current user's reports, recent reports, and validated reports
    user_reports = Report.query.filter_by(user_id=current_user.id).order_by(Report.created_at.desc()).all()

    # Get recent reports (latest 10)
    recent_reports = Report.query.order_by(Report.created_at.desc()).limit(10).all()

    # Get validated reports (status = 'auto_validated', latest 10)
    validated_reports = Report.query.filter_by(status='auto_validated').order_by(Report.created_at.desc()).limit(10).all()

    # For authority users, show all reports (recent 50)
    if current_user.user_type == 'authority':
        all_reports = Report.query.order_by(Report.created_at.desc()).limit(50).all()
    else:
        all_reports = []

    # Pass all needed lists into the template
    return render_template(
        'dashboard.html', 
        user_reports=user_reports, 
        all_reports=all_reports,
        recent_reports=recent_reports,
        validated_reports=validated_reports
    )



def simple_ai_validator(report_data):
    description = report_data.get('description', '').lower()
    severity = report_data.get('severity', 'medium').lower()
    suspicious_keywords = ['fake', 'false', 'spam', 'test', 'dummy']
    if any(word in description for word in suspicious_keywords):
        status = 'flagged'
        notes = 'Contains suspicious keywords.'
    elif severity in ['high', 'critical']:
        status = 'auto_validated'
        notes = 'High severity auto-validated.'
    else:
        status = 'pending'
        notes = 'Default pending status.'

    return {
        'validation_status': status,
        'validation_notes': notes,
        'confidence_score': 0.75 if status == 'auto_validated' else 0.3
    }


# Temporarily bypass login and mock current_user for testing
@app.route('/submit-report', methods=['POST'])
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

        if not all([title, description, incident_type, incident_date_str]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('report'))

        try:
            if not isinstance(incident_date_str, str) or not incident_date_str:
                raise ValueError("No date string provided")
            incident_date = datetime.strptime(incident_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('report'))

        photo_filename = None
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                photo_filename = f"{uuid.uuid4()}.{file_ext}"

                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
                file.save(file_path)

        # Mock current_user for testing
        class MockUser:
            id = 1

        global current_user
        current_user = MockUser()

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

        report_data = {
            "title": report.title,
            "description": report.description,
            "incident_type": report.incident_type,
            "severity": report.severity,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "photo_filename": report.photo_filename
        }

        ai_result = simple_ai_validator(report_data)

        report.status = ai_result.get("validation_status", "pending")
        report.validation_notes = ai_result.get("validation_notes", "")
        db.session.add(report)
        db.session.commit()

        flash(f'Report submitted. Status: {report.status}.', 'info')
        return redirect(url_for('dashboard'))

    except Exception as e:
        app.logger.error(f"Error submitting report: {str(e)}")
        flash('An error occurred while submitting your report. Please try again.', 'error')
        return redirect(url_for('report'))


@app.route('/api/reports')
def api_reports():
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
            'reporter': report.reporter.username if report.reporter else 'Unknown',
            'validation_notes': report.validation_notes
        })

    return jsonify(reports_data)


# Temporarily bypass login and mock current_user for testing
@app.route('/ai-insights')
def ai_insights():
    # Mock current_user for testing
    class MockUser:
        user_type = 'authority'

    global current_user
    current_user = MockUser()

    if current_user.user_type != 'authority':
        flash('Access denied. Authority privileges required.', 'error')
        return redirect(url_for('dashboard'))

    flagged_reports = Report.query.filter_by(status='flagged').all()
    validated_reports = Report.query.filter_by(status='auto_validated').all()
    pending_reports = Report.query.filter_by(status='pending').all()

    total_reports = Report.query.count()
    auto_validated = len(validated_reports)
    flagged_count = len(flagged_reports)

    ai_efficiency = (auto_validated / total_reports * 100) if total_reports > 0 else 0

    return render_template(
        'ai_insights.html',
        flagged_reports=flagged_reports,
        validated_reports=validated_reports[:10],
        pending_reports=pending_reports[:10],
        ai_efficiency=round(ai_efficiency, 1),
        total_reports=total_reports,
        auto_validated=auto_validated,
        flagged_count=flagged_count
    )


@app.route('/debug')
def debug():
    users = User.query.all()
    reports = Report.query.all()

    html = f"""
    <h2>Database Debug - Replit</h2>
    <p><strong>Total Users:</strong> {len(users)}</p>
    <p><strong>Total Reports:</strong> {len(reports)}</p>

    <h3>Users:</h3>
    <ul>
    """

    for user in users:
        html += f"<li>{user.username} - {user.email} - {user.user_type}</li>"

    html += """
    </ul>
    <h3>Reports with AI Analysis:</h3>
    <ul>
    """

    for report in reports:
        html += f"""<li>
        <strong>{report.title}</strong> - {report.incident_type} - 
        Status: <strong>{report.status}</strong> - 
        By: {report.reporter.username}<br>
        <small>AI Notes: {report.validation_notes or 'None'}</small>
        </li><br>"""

    html += "</ul><br><a href='/'>Back to Home</a>"
    return html


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
