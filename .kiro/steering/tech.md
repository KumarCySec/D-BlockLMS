# Technology Stack

## Backend Framework
- **Python 3.11+** - Primary language
- **Flask** - Web framework with blueprints architecture
- **SQLAlchemy** - ORM for database operations
- **Flask-Login** - Authentication management
- **Flask-Migrate + Alembic** - Database migrations
- **Marshmallow** - Data validation and serialization
- **bcrypt** - Password hashing
- **APScheduler** - Task scheduling (development only)
- **Cron jobs** - Scheduled tasks (production only)

## Frontend Stack
- **Bootstrap 5** - UI framework for responsive design
- **Vanilla JavaScript** - Minimal dependencies approach
- **Bootstrap Icons** - Icon library
- **HTML5** - Semantic markup
- **CSS3** - Custom styling with mobile-first approach
- **Service Worker** - PWA notifications support

## Database
- **SQLite** - Development database
- **PostgreSQL** - Production database
- **SQLite FTS5** - Full-text search (development)
- **PostgreSQL full-text search** - Production search

## Security & Authentication
- **HTTPS** - Required in production
- **CSRF Protection** - All forms protected
- **Rate Limiting** - Login attempts and API calls
- **PII Encryption** - Sensitive data protection
- **Session-based Authentication** - Flask-Login sessions

## Development Tools
- **Git** - Version control
- **Virtual Environment** - Python dependency isolation
- **Flask CLI** - Command-line interface
- **pytest** - Testing framework (planned)

## Deployment
- **PythonAnywhere** - Production hosting
- **Cron jobs** - Scheduled tasks in production
- **WSGI** - Web server interface

## Common Commands

### Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
```

### Database Operations
```bash
# Initialize database
flask db init

# Create migration
flask db migrate -m "Description"

# Apply migrations
flask db upgrade

# Seed initial data
flask seed-data
```

### Development
```bash
# Run development server
flask run

# Run with debug mode
flask run --debug

# Run on specific port
flask run --port 8000

# Run tests
pytest

# Run tests with coverage
pytest --cov=app
```

### Production Deployment
```bash
# Install production dependencies
pip install -r requirements.txt

# Set production environment
export FLASK_ENV=production

# Run database migrations
flask db upgrade

# Collect static files (if applicable)
flask collect-static
```

## Notification Infrastructure
- **Database Queue**: Persistent notification storage with retry mechanism
- **Background Processing**: Cron jobs for notification delivery (production)
- **Multi-Channel Support**: Web Push API, SMS gateway, Email service
- **Retry Logic**: Exponential backoff for failed deliveries
- **Delivery Tracking**: Status monitoring and failure alerting

## Audit Logging & Monitoring
- **Structured Logging**: JSON format with consistent fields
- **Security Events**: Login attempts, permission changes, data access
- **Business Events**: Transactions, approvals, inventory changes
- **Error Capture**: Exception tracking with stack traces
- **Performance Monitoring**: Response times, database query performance
- **Log Retention**: 90-day retention policy with archival

## PII Encryption Strategy
- **Encrypted Fields**: Phone numbers, email addresses, personal addresses
- **Encryption Method**: AES-256 with application-level encryption
- **Key Management**: Environment variables with rotation capability
- **Database Storage**: Encrypted data stored as binary/text fields
- **Access Control**: Decryption only for authorized roles
- **Compliance**: Data protection regulations adherence

## Testing Requirements
- **Test Coverage**: >90% minimum requirement
- **Unit Tests**: All models, services, and utility functions
- **Integration Tests**: Complete user workflows and API endpoints
- **Security Tests**: Authentication, authorization, and data protection
- **Performance Tests**: Load testing for critical paths
- **Mobile Tests**: Responsive design and touch interface validation

## Code Style Guidelines
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Implement comprehensive error handling
- Write docstrings for all functions and classes
- Use meaningful variable and function names
- Keep functions small and focused
- Implement proper logging throughout the application
- Maintain >90% test coverage for all new code