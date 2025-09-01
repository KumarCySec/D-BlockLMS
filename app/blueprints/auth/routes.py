"""
Authentication routes
"""
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from app.blueprints.auth import bp
from app.models.user import User, UserStatus
from app.models.role import Role
from app.models.department import Department
from app.utils.auth import login_required_with_status
from app.utils.audit import AuditService, audit_login_attempts
from app.utils.validation import validate_registration_data, validate_login_data
from app import db, limiter


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute") if limiter else lambda f: f
def login():
    """User login with rate limiting and security checks"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        # Basic validation
        if not email or not password:
            flash('Please provide both email and password', 'error')
            return render_template('auth/login.html')
        
        # Check for rate limiting (simple session-based)
        login_attempts = session.get('login_attempts', 0)
        if login_attempts >= 5:
            flash('Too many failed login attempts. Please try again later.', 'error')
            return render_template('auth/login.html')
        
        user = User.get_by_email(email)
        
        if user and user.check_password(password):
            if user.status == UserStatus.PENDING:
                flash('Your account is pending approval. Please wait for an administrator to activate your account.', 'warning')
                return render_template('auth/login.html')
            elif user.status == UserStatus.SUSPENDED:
                flash('Your account has been suspended. Please contact an administrator.', 'error')
                return render_template('auth/login.html')
            elif user.status == UserStatus.INACTIVE:
                flash('Your account is inactive. Please contact an administrator.', 'error')
                return render_template('auth/login.html')
            elif user.is_active_user():
                # Successful login
                login_user(user, remember=True)
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                # Log successful login
                AuditService.log_login_success(user)
                
                # Clear login attempts
                session.pop('login_attempts', None)
                
                # Redirect to next page or dashboard
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    return redirect(next_page)
                return redirect(url_for('main.dashboard'))
        
        # Failed login
        session['login_attempts'] = login_attempts + 1
        AuditService.log_login_failure(email, "Invalid credentials")
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')


@bp.route('/logout')
@login_required_with_status
def logout():
    """User logout"""
    # Log logout before clearing session
    AuditService.log_logout(current_user)
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute") if limiter else lambda f: f
def register():
    """User registration with validation"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        # Get form data
        form_data = {
            'name': request.form.get('name', '').strip(),
            'roll_number': request.form.get('roll_number', '').strip().upper(),
            'branch': request.form.get('branch', '').strip(),
            'batch': request.form.get('batch', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'email': request.form.get('email', '').strip().lower(),
            'password': request.form.get('password', ''),
            'confirm_password': request.form.get('confirm_password', '')
        }
        
        # Validate using Marshmallow schema
        validated_data, validation_errors = validate_registration_data(form_data)
        
        if validation_errors:
            for field, messages in validation_errors.items():
                if isinstance(messages, list):
                    for message in messages:
                        flash(message, 'error')
                else:
                    flash(messages, 'error')
            return render_template('auth/register.html')
        
        try:
            # Auto-link department based on branch
            department = Department.get_department_by_branch(validated_data['branch'])
            
            # Create user
            user = User.create_user(
                name=validated_data['name'],
                roll_number=validated_data['roll_number'],
                branch=validated_data['branch'],
                batch=validated_data['batch'],
                phone=validated_data['phone'],
                email=validated_data['email'],
                password=validated_data['password'],
                department_id=department.id if department else None
            )
            
            # Assign default Student role
            student_role = Role.get_by_name('Student')
            if student_role:
                user.roles.append(student_role)
            
            db.session.add(user)
            db.session.commit()
            
            # Log user registration
            AuditService.log_user_registration(user)
            
            flash('Registration successful! Please wait for approval from an administrator.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')