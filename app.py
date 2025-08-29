"""
Application entry point for D-Block Library Management System
"""
import os
from dotenv import load_dotenv
from app import create_app, db
from app.models.user import User
from app.models.role import Role
from app.models.department import Department

# Load environment variables
load_dotenv()

# Create Flask application
app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Make database models available in Flask shell"""
    return {
        'db': db,
        'User': User,
        'Role': Role,
        'Department': Department
    }


@app.cli.command()
def init_db():
    """Initialize database with default data"""
    db.create_all()
    
    # Create default roles
    roles = Role.create_default_roles()
    print(f"Created {len(roles)} default roles")
    
    # Create default departments
    departments = Department.create_default_departments()
    print(f"Created {len(departments)} default departments")
    
    print("Database initialized successfully!")


@app.cli.command()
def create_admin():
    """Create admin user"""
    name = input("Admin name: ")
    email = input("Admin email: ")
    password = input("Admin password: ")
    
    # Check if admin already exists
    if User.get_by_email(email):
        print("User with this email already exists!")
        return
    
    # Create admin user
    admin = User.create_user(
        name=name,
        roll_number="ADMIN001",
        branch="Administration",
        batch="ADMIN",
        phone="0000000000",
        email=email,
        password=password
    )
    
    # Set status to active
    from app.models.user import UserStatus
    admin.status = UserStatus.ACTIVE
    
    # Assign admin role
    admin_role = Role.get_by_name('Admin')
    if admin_role:
        admin.roles.append(admin_role)
    
    db.session.add(admin)
    db.session.commit()
    
    print(f"Admin user '{name}' created successfully!")


if __name__ == '__main__':
    app.run(debug=True)