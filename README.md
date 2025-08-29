# D-Block Library Management System

A mobile-first library management system designed specifically for D-Block Ladies Hostel, supporting inventory management, approval-based checkout workflows, volunteer scheduling, and comprehensive analytics.

## 🎯 Project Overview

The D-Block Library Management System is a comprehensive web application that manages:

- **Inventory Management**: Books, Laptops, and Kits donated by alumni
- **User Roles**: Admin, Incharge, Volunteer, and Student with hierarchical permissions
- **Approval Workflow**: Request-based checkout system with volunteer/incharge approval
- **Volunteer Management**: Scheduling, attendance tracking, and performance monitoring
- **Fine Management**: Configurable fine calculation with waiver capabilities
- **Analytics & Reporting**: Role-based dashboards and comprehensive reporting
- **Mobile-First Design**: Optimized for mobile devices with responsive UI

## 🏗️ Architecture

- **Backend**: Python 3.11+ with Flask framework
- **Database**: SQLite (development) / PostgreSQL (production)
- **Frontend**: HTML5 + Bootstrap 5 + Vanilla JavaScript
- **Authentication**: Flask-Login with bcrypt password hashing
- **Notifications**: Web Push API with future SMS/Email support
- **Deployment**: PythonAnywhere with scheduled tasks

## 📋 Features

### Core Features

- ✅ User registration with approval workflow
- ✅ Inventory management with donor tracking
- ✅ Request-based checkout with approval system
- ✅ Renewal management with 4-renewal limit
- ✅ Waitlist system with FIFO queue
- ✅ Fine calculation with configurable rules
- ✅ Volunteer scheduling and attendance tracking
- ✅ Library status management (open/closed)
- ✅ Comprehensive search and filtering
- ✅ Real-time notifications
- ✅ Analytics and reporting
- ✅ Audit trails for all operations

### Advanced Features

- ✅ Mobile-first responsive design
- ✅ Role-based access control
- ✅ PII encryption and data protection
- ✅ Professional transaction IDs (LIB2025-0001)
- ✅ Configurable fine rules per item type
- ✅ Department rotation scheduling
- ✅ Attendance tracking with performance metrics
- ✅ Multi-channel notification system
- ✅ CSV export functionality
- ✅ Comprehensive audit logging

## 📁 Project Structure

```
D-BlockLMS/
├── .kiro/
│   ├── specs/library-management-system/
│   │   ├── requirements.md    # 28 detailed requirements
│   │   ├── design.md         # Complete technical design
│   │   └── tasks.md          # 43 implementation tasks
│   └── steering/             # AI assistant guidance
│       ├── product.md        # Product overview and success metrics
│       ├── tech.md          # Technology stack and development commands
│       └── structure.md     # Project organization and conventions
├── app/                     # Flask application (to be created)
├── tests/                   # Test suite (to be created)
├── migrations/              # Database migrations (to be created)
└── README.md               # This file
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Git
- Virtual environment support

### Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/KumarCySec/D-BlockLMS.git
   cd D-BlockLMS
   ```

2. Create and activate virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies (after implementation begins):

   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize database:

   ```bash
   flask db upgrade
   flask seed-data
   ```

6. Run the application:
   ```bash
   flask run
   ```

## 📖 Implementation Plan

The project is organized into 10 phases with 43 specific tasks:

1. **Phase 1**: Foundation & Core Infrastructure
2. **Phase 2**: Inventory & Donor Management
3. **Phase 3**: Transaction & Approval Workflow
4. **Phase 4**: Renewals, Returns & Waitlist System
5. **Phase 5**: Volunteer Management & Scheduling
6. **Phase 6**: Notification System & Background Jobs
7. **Phase 7**: Analytics, Reporting & Fine Management
8. **Phase 8**: User Management & Advanced Features
9. **Phase 9**: System Configuration & Administration
10. **Phase 10**: Testing, Optimization & Deployment

See [tasks.md](.kiro/specs/library-management-system/tasks.md) for detailed implementation tasks.

## 🔧 Technology Stack

### Backend

- **Framework**: Flask with blueprints
- **ORM**: SQLAlchemy
- **Authentication**: Flask-Login + bcrypt
- **Validation**: Marshmallow
- **Migrations**: Flask-Migrate + Alembic
- **Scheduling**: APScheduler (dev) / Cron jobs (production)

### Frontend

- **UI Framework**: Bootstrap 5
- **JavaScript**: Vanilla JS with minimal libraries
- **Icons**: Bootstrap Icons
- **Responsive**: Mobile-first design
- **PWA**: Service Worker for notifications

### Database

- **Development**: SQLite
- **Production**: PostgreSQL
- **Search**: SQLite FTS5 / PostgreSQL full-text search

### Security

- **HTTPS**: Required in production
- **CSRF**: Protection for all forms
- **Rate Limiting**: Login attempts and API calls
- **PII Encryption**: Sensitive data protection
- **Audit Logging**: Complete action trails

## 👥 User Roles

1. **Admin**: System-wide access, user management, configuration
2. **Incharge**: Department management, user approval, analytics
3. **Volunteer**: Transaction approval, library status, daily operations
4. **Student**: Item requests, renewals, profile management

## 📊 Key Metrics

- **Transaction ID Format**: LIB2025-0001 (professional format)
- **Renewal Limit**: 4 renewals per item
- **Fine Calculation**: Configurable per item type
- **Waitlist**: FIFO with 24-hour claim window
- **Mobile Support**: 320px+ screen width
- **Response Time**: <500ms average
- **Test Coverage**: >90% target

## 🔒 Security Features

- Bcrypt password hashing
- Session-based authentication
- Role-based access control
- CSRF protection
- Rate limiting
- PII encryption
- Audit logging
- Data retention policies

## 📱 Mobile-First Design

- Touch-friendly interface (44px+ touch targets)
- Responsive breakpoints
- Bottom navigation for mobile
- Optimized forms and inputs
- Fast loading and minimal data usage

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Designed for D-Block Ladies Hostel Library
- Built with modern web technologies
- Focused on user experience and accessibility
- Community-driven development approach

## 🤖 AI Assistant Guidance

The project includes comprehensive steering documentation in `.kiro/steering/` to guide AI assistants:

- **product.md**: Product overview, core purpose, success metrics, and scope boundaries
- **tech.md**: Complete technology stack, development commands, and coding standards
- **structure.md**: Project organization, naming conventions, and architectural patterns

These documents ensure consistent development practices and provide context for AI-assisted development.

---

**Status**: 📋 Specification & Steering Complete - Ready for Implementation  
**Next Step**: Begin Phase 1 implementation tasks  
**Repository**: https://github.com/KumarCySec/D-BlockLMS.git
