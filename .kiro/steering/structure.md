# Project Structure

## Directory Organization

```
D-BlockLMS/
├── .kiro/
│   ├── specs/library-management-system/    # Project specifications
│   │   ├── requirements.md                 # 28 detailed requirements
│   │   ├── design.md                      # Complete technical design
│   │   └── tasks.md                       # 43 implementation tasks
│   └── steering/                          # AI assistant guidance
├── app/                                   # Flask application (main package)
│   ├── __init__.py                       # App factory
│   ├── models/                           # SQLAlchemy models
│   ├── blueprints/                       # Flask blueprints
│   │   ├── auth/                         # Authentication routes
│   │   ├── inventory/                    # Inventory management
│   │   ├── transactions/                 # Checkout/return workflows
│   │   ├── volunteers/                   # Volunteer management
│   │   ├── admin/                        # Admin panel
│   │   └── api/                          # API endpoints
│   ├── templates/                        # Jinja2 templates
│   │   ├── base.html                     # Base template
│   │   ├── auth/                         # Authentication templates
│   │   ├── inventory/                    # Inventory templates
│   │   └── components/                   # Reusable components
│   ├── static/                           # Static assets
│   │   ├── css/                          # Custom stylesheets
│   │   ├── js/                           # JavaScript files
│   │   └── images/                       # Image assets
│   ├── utils/                            # Utility functions
│   └── config.py                         # Configuration settings
├── migrations/                           # Database migrations
├── tests/                                # Test suite
│   ├── unit/                            # Unit tests
│   ├── integration/                     # Integration tests
│   ├── fixtures/                        # Test data and factories
│   └── factories/                       # Test data factories for TDD
├── requirements.txt                      # Python dependencies
├── .env.example                         # Environment variables template
├── .gitignore                           # Git ignore rules
└── README.md                            # Project documentation
```

## Flask Application Structure

### Blueprints Organization
- **auth**: User registration, login, logout, profile management
- **inventory**: Item management, donor tracking, search functionality
- **transactions**: Checkout requests, approvals, returns, renewals
- **volunteers**: Scheduling, attendance, performance tracking
- **admin**: System configuration, user management, analytics
- **api**: RESTful endpoints for AJAX operations

### Models Structure
- **User**: Authentication, role management, profile information
- **Inventory**: Books, laptops, kits with donor information and availability
- **Donor**: Alumni donor information and contribution tracking
- **Transaction**: Checkout/return records with approval workflow
- **Renewal**: Renewal requests and history (4 renewal limit)
- **Waitlist**: FIFO queue management with 24-hour claim window
- **Fine**: Configurable fine calculation and waiver management
- **Volunteer**: Scheduling, attendance tracking, and performance metrics
- **VolunteerSchedule**: Department rotation and shift management
- **Notification**: Multi-channel notifications (Web Push, SMS, Email)
- **AuditLog**: Complete activity tracking and security logging
- **LibraryStatus**: Open/closed status and operational hours
- **SystemConfig**: Configurable system settings and fine rules

### Templates Organization
- Use Jinja2 inheritance with base.html
- Mobile-first responsive design with Bootstrap 5
- Component-based approach for reusable UI elements
- Separate templates for each major feature area

## Naming Conventions

### Files and Directories
- Use lowercase with underscores for Python files: `user_model.py`
- Use kebab-case for templates: `user-profile.html`
- Use camelCase for JavaScript files: `userManagement.js`
- Use lowercase for CSS files: `custom.css`

### Python Code
- Classes: PascalCase (`UserModel`, `TransactionService`)
- Functions/methods: snake_case (`get_user_by_id`, `process_checkout`)
- Constants: UPPER_SNAKE_CASE (`MAX_RENEWALS`, `TRANSACTION_PREFIX`)
- Variables: snake_case (`user_id`, `checkout_date`)

### Database
- Table names: lowercase with underscores (`users`, `inventory_items`)
- Column names: lowercase with underscores (`created_at`, `user_id`)
- Foreign keys: `{table}_id` format (`user_id`, `inventory_id`)

## Configuration Management
- Use environment variables for sensitive data
- Separate configurations for development, testing, production
- Store configuration in `app/config.py`
- Use `.env` files for local development

## Security Considerations
- All routes require appropriate role-based permissions
- CSRF protection on all forms
- Input validation using Marshmallow schemas
- Audit logging for all significant operations
- PII encryption for sensitive user data

## Mobile-First Design Principles
- Touch-friendly interface (44px+ touch targets)
- Responsive breakpoints: 320px, 768px, 1024px
- Bottom navigation for mobile devices
- Optimized forms and inputs for mobile
- Fast loading with minimal data usage

## Testing Strategy
- Test-Driven Development (TDD) approach
- Factory pattern for test data generation
- Comprehensive fixtures for integration tests
- >90% test coverage requirement
- Unit tests for all models and services
- Integration tests for complete workflows

## Future-Proofing Considerations
- API-first design for potential SPA migration
- Clear separation between business logic and presentation
- RESTful endpoints ready for mobile app integration
- Modular architecture supporting microservices transition