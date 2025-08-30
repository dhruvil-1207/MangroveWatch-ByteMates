import os
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, Report
import uuid
import re

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# HARDCODED AI VALIDATION FUNCTIONS
def validate_mangrove_coordinates(lat, lng):
    """Basic geological validation for mangrove locations"""
    if not lat or not lng:
        return False, "Location coordinates required"
    
    # Known mangrove regions (hardcoded coastal areas)
    mangrove_zones = [
        {"name": "Western India Coast", "lat_min": 8.0, "lat_max": 23.0, "lng_min": 68.0, "lng_max": 78.0},
        {"name": "Eastern India Coast", "lat_min": 8.0, "lat_max": 22.0, "lng_min": 80.0, "lng_max": 93.0},
        {"name": "Southeast Asia", "lat_min": -10.0, "lat_max": 25.0, "lng_min": 95.0, "lng_max": 140.0},
        {"name": "Gulf Coast USA", "lat_min": 24.0, "lat_max": 31.0, "lng_min": -98.0, "lng_max": -80.0},
        {"name": "Caribbean", "lat_min": 10.0, "lat_max": 27.0, "lng_min": -85.0, "lng_max": -60.0},
    ]
    
    lat, lng = float(lat), float(lng)
    
    for zone in mangrove_zones:
        if (zone["lat_min"] <= lat <= zone["lat_max"] and 
            zone["lng_min"] <= lng <= zone["lng_max"]):
            return True, f"Location validated in {zone['name']}"
    
    return False, "Location not in known mangrove habitat zone"

def calculate_report_credibility(user, title, description, incident_type):
    """AI-like credibility scoring"""
    score = 100
    flags = []
    
    # User history check
    user_reports = Report.query.filter_by(user_id=user.id).count()
    if user_reports > 10:
        score += 20  # Trusted reporter
    elif user_reports == 0:
        score -= 10  # New user
    
    # Spam detection
    spam_keywords = ['urgent', 'immediate', 'crisis', 'emergency', 'help help']
    spam_count = sum(1 for word in spam_keywords if word.lower() in title.lower() or word.lower() in description.lower())
    if spam_count > 2:
        score -= 30
        flags.append("Potential spam detected")
    
    # Description quality check
    if len(description) < 20:
        score -= 15
        flags.append("Description too brief")
    elif len(description) > 500:
        score += 10  # Detailed report
    
    # Incident type validation
    valid_types = ['illegal_cutting', 'pollution', 'construction', 'dumping', 'erosion']
    if incident_type not in valid_types:
        score -= 20
        flags.append("Invalid incident type")
    
    # Recent duplicate check
    recent_reports = Report.query.filter(
        Report.user_id == user.id,
        Report.created_at > datetime.utcnow() - timedelta(hours=24)
    ).count()
    
    if recent_reports > 5:
        score -= 25
        flags.append("Too many reports in 24h")
    
    return max(0, min(100, score)), flags

def analyze_photo_metadata(filename):
    """Basic photo validation"""
    if not filename:
        return 70, ["No photo provided"]
    
    # File extension check
    valid_extensions = ['jpg', 'jpeg', 'png']
    ext = filename.split('.')[-1].lower()
    
    if ext not in valid_extensions:
        return 20, ["Invalid photo format"]
    
    # Mock AI analysis (in real app, this would use computer vision)
    return 85, ["Photo appears authentic"]

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
        
        # Basic validation
        if not all([title, description, incident_type, incident_date_str]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('report'))
        
        # AI VALIDATION - Location Check
        if latitude and longitude:
            location_valid, location_msg = validate_mangrove_coordinates(latitude, longitude)
            if not location_valid:
                flash(f'Location Validation Failed: {location_msg}', 'error')
                return redirect(url_for('report'))
            flash(f'Location Verified: {location_msg}', 'success')
        
        # AI VALIDATION - Report Credibility
        credibility_score, credibility_flags = calculate_report_credibility(
            current_user, title, description, incident_type
        )
        
        # Parse incident date
        try:
            if not isinstance(incident_date_str, str) or not incident_date_str:
                raise ValueError("No date string provided")
            incident_date = datetime.strptime(incident_date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format.', 'error')
            return redirect(url_for('report'))
        
        # Handle file upload with AI validation
        photo_filename = None
        photo_score = 70
        if 'photo' in request.files:
            file = request.files['photo']
            if file and file.filename and allowed_file(file.filename):
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                photo_filename = f"{uuid.uuid4()}.{file_ext}"
                
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
                file.save(file_path)
                
                # AI Photo Analysis
                photo_score, photo_flags = analyze_photo_metadata(photo_filename)
                credibility_flags.extend(photo_flags)
        
        # Determine auto-validation based on AI scores
        auto_status = 'pending'
        if credibility_score >= 80 and photo_score >= 75:
            auto_status = 'validated'
        elif credibility_score < 40:
            auto_status = 'flagged'
        
        # Create report with AI analysis
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
        report.status = auto_status
        
        # Add AI validation notes
        if credibility_flags:
            report.validation_notes = f"AI Analysis (Score: {credibility_score}%): " + "; ".join(credibility_flags)
        
        db.session.add(report)
        db.session.commit()
        
        # Different messages based on AI validation
        if auto_status == 'validated':
            flash(f'Report auto-validated! (AI Confidence: {credibility_score}%) Thank you for the quality submission.', 'success')
        elif auto_status == 'flagged':
            flash(f'Report flagged for review (AI Score: {credibility_score}%). Authorities will investigate.', 'warning')
        else:
            flash(f'Report submitted (AI Score: {credibility_score}%). Pending validation.', 'info')
        
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
            'reporter': report.reporter.username if report.reporter else 'Unknown',
            'validation_notes': report.validation_notes
        })
    
    return jsonify(reports_data)

# NEW: AI Validation Dashboard for Authorities
@app.route('/ai-insights')
@login_required
def ai_insights():
    if current_user.user_type != 'authority':
        flash('Access denied. Authority privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get flagged reports
    flagged_reports = Report.query.filter_by(status='flagged').all()
    validated_reports = Report.query.filter_by(status='validated').all()
    pending_reports = Report.query.filter_by(status='pending').all()
    
    # Calculate AI stats
    total_reports = Report.query.count()
    auto_validated = len(validated_reports)
    flagged_count = len(flagged_reports)
    
    ai_efficiency = (auto_validated / total_reports * 100) if total_reports > 0 else 0
    
    return render_template('ai_insights.html', 
                         flagged_reports=flagged_reports,
                         validated_reports=validated_reports[:10],  # Show recent 10
                         pending_reports=pending_reports[:10],
                         ai_efficiency=round(ai_efficiency, 1),
                         total_reports=total_reports,
                         auto_validated=auto_validated,
                         flagged_count=flagged_count)

# DEBUG ROUTE
@app.route('/debug')
def debug():
    from models import User, Report
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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500