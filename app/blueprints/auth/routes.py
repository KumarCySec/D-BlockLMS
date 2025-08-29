"""
Authentication routes
"""
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from app.blueprints.auth import bp
from app.models.user import User
from app import db


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.get_by_email(email)
        if user and user.check_password(password) and user.is_active_user():
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')


@bp.route('/logout')
def logout():
    """User logout"""
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        branch = request.form.get('branch')
        batch = request.form.get('batch')
        phone = request.form.get('phone')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user already exists
        if User.get_by_email(email):
            flash('Email already registered', 'error')
            return render_template('auth/register.html')
        
        if User.get_by_roll_number(roll_number):
            flash('Roll number already registered', 'error')
            return render_template('auth/register.html')
        
        # Auto-link department based on branch
        from app.models.department import Department
        department = Department.get_department_by_branch(branch)
        
        # Create user
        user = User.create_user(
            name=name,
            roll_number=roll_number,
            branch=branch,
            batch=batch,
            phone=phone,
            email=email,
            password=password,
            department_id=department.id if department else None
        )
        
        # Assign default Student role
        from app.models.role import Role
        student_role = Role.get_by_name('Student')
        if student_role:
            user.roles.append(student_role)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please wait for approval.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')