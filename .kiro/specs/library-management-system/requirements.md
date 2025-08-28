# Requirements Document

## Introduction

The D-Block Library Management System is a mobile-first web application designed to manage inventory (Books, Laptops, Kits) donated by alumni for a ladies hostel library. The system supports four distinct roles (Admin > Incharge > Volunteer > Student) with an approval-based checkout workflow, volunteer scheduling, donor tracking, request management, notifications, and analytics capabilities.

## Requirements

### Requirement 1: User Authentication and Role Management

**User Story:** As a library system user, I want to register and be assigned appropriate roles so that I can access features relevant to my responsibilities.

#### Acceptance Criteria

1. WHEN a new user registers THEN the system SHALL create an account with "pending" status requiring approval
2. WHEN registering THEN the system SHALL capture mandatory fields: name, roll number, branch, batch, phone, and email
3. WHEN an Incharge or Admin approves a pending user THEN the system SHALL activate the account and allow login
4. WHEN a user logs in THEN the system SHALL authenticate using bcrypt-hashed passwords and establish a secure session
5. IF a user has multiple roles THEN the system SHALL provide access to all combined permissions
6. WHEN login attempts exceed the rate limit THEN the system SHALL temporarily block further attempts

### Requirement 2: Inventory Management

**User Story:** As an Admin or Incharge, I want to manage library inventory including books, laptops, and kits so that I can track all donated items and their availability.

#### Acceptance Criteria

1. WHEN adding inventory items THEN the system SHALL capture item type, title, authors, language, donor information, and quantity
2. WHEN an item is checked out THEN the system SHALL decrement available_quantity and prevent over-allocation
3. WHEN an item is returned THEN the system SHALL increment available_quantity
4. WHEN viewing inventory THEN the system SHALL display current availability, donor information, and item history
5. IF available_quantity reaches zero THEN the system SHALL mark the item as unavailable for checkout

### Requirement 3: Donor Tracking

**User Story:** As an Admin or Incharge, I want to track alumni donors and their contributions so that I can maintain donor relationships and acknowledge contributions.

#### Acceptance Criteria

1. WHEN adding a donor THEN the system SHALL capture name, branch, batch, address, phone, email, and donation history
2. WHEN viewing inventory items THEN the system SHALL display associated donor information
3. WHEN generating reports THEN the system SHALL provide donor contribution summaries
4. WHEN editing donor information THEN the system SHALL maintain audit trails of changes

### Requirement 4: Checkout and Approval Workflow

**User Story:** As a Student, I want to request library items so that I can borrow materials for my studies with proper approval.

#### Acceptance Criteria

1. WHEN a student requests an item THEN the system SHALL create a transaction with "requested" status
2. WHEN a Volunteer, Incharge, or Admin reviews the request THEN the system SHALL allow approval or rejection with notes
3. WHEN a request is approved THEN the system SHALL generate a unique transaction ID (format: DBL-YYYYMMDD-XXXX)
4. WHEN a request is approved THEN the system SHALL set due date and update item availability
5. WHEN a transaction is created THEN the system SHALL notify assigned volunteers and incharge
6. WHEN implementing transaction lifecycle THEN the system SHALL enforce the following states and transitions:
   - Status set: {requested, approved, rejected, borrowed, returned, overdue, cancelled}
   - Transitions: requested → (approved | rejected | cancelled); approved → borrowed (on issue); borrowed → (returned | overdue); returned → closed
   - Cancelled status can only be set before approval
7. WHEN processing approval operations THEN the system SHALL execute availability check and quantity decrement atomically in a single database transaction
8. WHEN generating transaction IDs THEN the system SHALL use database sequence/counter with atomic increment per day to guarantee uniqueness under concurrent approvals

### Requirement 5: Renewal and Return Management

**User Story:** As a Student, I want to renew or return borrowed items so that I can extend my borrowing period or complete transactions properly.

#### Acceptance Criteria

1. WHEN a student requests renewal THEN the system SHALL require approval from authorized personnel
2. WHEN renewal count reaches 4 THEN the system SHALL block further renewal requests
3. WHEN a student requests return THEN the system SHALL require approval to complete the transaction
4. WHEN items are overdue THEN the system SHALL calculate fines based on configurable daily rates (calculation only, no payment processing)
5. WHEN return is approved THEN the system SHALL update availability and clear the transaction
6. WHEN fines are calculated THEN the system SHALL display amounts for monitoring by higher authorities without payment integration
7. WHEN an item has an active waitlist THEN automatic renewal requests SHALL be blocked and renewal MAY be allowed only with explicit approval by Incharge/Admin

### Requirement 6: Waitlist and Request Management

**User Story:** As a Student, I want to join a waitlist for unavailable items so that I can be notified when they become available.

#### Acceptance Criteria

1. WHEN an item is unavailable THEN the system SHALL allow students to join a waitlist
2. WHEN an item becomes available THEN the system SHALL notify the next person in queue (FIFO)
3. WHEN a waitlisted item is returned THEN the system SHALL automatically notify the next eligible student
4. WHEN viewing item details THEN the system SHALL display current waitlist position

### Requirement 7: Volunteer Scheduling

**User Story:** As an Incharge, I want to schedule volunteers for daily library management so that there are always two volunteers available per department.

#### Acceptance Criteria

1. WHEN creating schedules THEN the system SHALL assign exactly two volunteers per department per day
2. WHEN viewing today's schedule THEN the system SHALL display current volunteers with contact details
3. WHEN editing schedules THEN the system SHALL allow override of default assignments
4. WHEN students view the library THEN the system SHALL show today's assigned volunteers
5. WHEN handling scheduling constraints THEN detailed validation and exception handling SHALL be covered under Requirement 24

### Requirement 8: Library Status Management

**User Story:** As a Volunteer or Incharge, I want to toggle library open/closed status so that students know when the library is available.

#### Acceptance Criteria

1. WHEN toggling library status THEN the system SHALL update open/closed state immediately
2. WHEN library is closed THEN the system SHALL allow setting next estimated open time
3. WHEN students access the system THEN the system SHALL prominently display current library status
4. WHEN status changes THEN the system SHALL log the change with timestamp and user
5. WHEN implementing automated status management THEN automated closure rules SHALL be covered under Requirement 28

### Requirement 9: Search and Filtering

**User Story:** As any user, I want to search and filter inventory so that I can quickly find relevant items.

#### Acceptance Criteria

1. WHEN searching inventory THEN the system SHALL support full-text search across titles, authors, and descriptions
2. WHEN applying filters THEN the system SHALL support filtering by department, language, donor, and availability
3. WHEN combining filters THEN the system SHALL allow multiple filters to be applied simultaneously (e.g., Dept = ECE + Availability = Yes + Sort by Popularity)
4. WHEN sorting results THEN the system SHALL support sorting by popularity, date added, and alphabetical order
5. WHEN viewing search results THEN the system SHALL display relevant item information and availability status

### Requirement 10: Notifications System

**User Story:** As a user, I want to receive timely notifications about due dates, approvals, and availability so that I can manage my library interactions effectively.

#### Acceptance Criteria

1. WHEN items are due tomorrow THEN the system SHALL send reminder notifications
2. WHEN requests are approved or rejected THEN the system SHALL notify the requesting student
3. WHEN waitlisted items become available THEN the system SHALL notify the next person in queue
4. WHEN notifications are sent THEN the system SHALL use mobile web push notifications as primary method
5. WHEN configuring notifications THEN the system SHALL support email and SMS as optional channels
6. WHEN users access notifications THEN the system SHALL allow opt-in/out of notification channels with explicit permission for web push
7. WHEN sending notifications THEN the system SHALL enforce rate limiting (maximum 3 notifications per item per day)

### Requirement 11: Analytics and Reporting

**User Story:** As an Admin or Incharge, I want to view analytics and generate reports so that I can understand library usage patterns and make informed decisions.

#### Acceptance Criteria

1. WHEN viewing analytics THEN the system SHALL display borrowing statistics, popular items, and overdue summaries
2. WHEN generating reports THEN the system SHALL provide donor contribution summaries and inventory reports
3. WHEN exporting data THEN the system SHALL support CSV export of transaction records
4. WHEN viewing dashboards THEN the system SHALL display real-time metrics and trends
5. WHEN accessing fine reports THEN detailed fine reporting SHALL be covered under Requirement 22

### Requirement 12: Mobile-First User Interface

**User Story:** As a user accessing the library system on mobile devices, I want a responsive and touch-friendly interface so that I can easily use all features on my phone.

#### Acceptance Criteria

1. WHEN accessing on mobile devices THEN the system SHALL provide optimal layout for screens as small as 320px width
2. WHEN interacting with UI elements THEN the system SHALL provide touch targets of at least 44px
3. WHEN viewing content THEN the system SHALL use readable font sizes (minimum 16px base)
4. WHEN navigating THEN the system SHALL provide intuitive mobile navigation with bottom tabs
5. WHEN using forms THEN the system SHALL provide mobile-optimized input fields and validation

### Requirement 13: Security and Privacy

**User Story:** As a system administrator, I want robust security measures so that user data and library operations are protected.

#### Acceptance Criteria

1. WHEN storing passwords THEN the system SHALL use bcrypt hashing with no plaintext storage
2. WHEN accessing the system THEN the system SHALL require HTTPS in production environments
3. WHEN handling PII THEN the system SHALL store minimal personal information and restrict export capabilities
4. WHEN performing sensitive operations THEN the system SHALL create audit logs for all transactions
5. WHEN implementing API endpoints THEN the system SHALL include CSRF protection and role-based access control
6. WHEN managing user accounts THEN Admin SHALL have permanent delete rights, Incharge SHALL have deactivate/reactivate rights for their department, Volunteers SHALL have no delete rights
7. WHEN elevating roles THEN only Admin SHALL be able to grant Admin role to other users

### Requirement 14: Data Management and Audit

**User Story:** As an Admin, I want comprehensive audit trails and data management capabilities so that I can track all system activities and maintain data integrity.

#### Acceptance Criteria

1. WHEN any transaction occurs THEN the system SHALL create detailed audit log entries
2. WHEN viewing item history THEN the system SHALL display complete borrowing history and current status
3. WHEN viewing user profiles THEN the system SHALL show current and past checkouts with due dates
4. WHEN managing data THEN the system SHALL support full CRUD operations for all entities with proper authorization
5. WHEN exporting data THEN the system SHALL maintain data retention policies and configurable export restrictions

### Requirement 15: Department Management

**User Story:** As an Admin or Incharge, I want to manage departments dynamically so that I can add new departments as the institution grows.

#### Acceptance Criteria

1. WHEN managing departments THEN the system SHALL provide default departments (CSE, ECE, EEE, CIVIL, AUTO, MECH, IT)
2. WHEN adding departments THEN the system SHALL allow creation of new departments with name and description
3. WHEN editing departments THEN the system SHALL allow modification of existing department details
4. WHEN deleting departments THEN the system SHALL prevent deletion if users or inventory are associated
5. WHEN viewing departments THEN the system SHALL display all active departments with usage statistics

### Requirement 16: Detailed Item and User Views

**User Story:** As any user, I want to access detailed information about items and users through click-through navigation so that I can get comprehensive insights.

#### Acceptance Criteria

1. WHEN clicking on an item THEN the system SHALL display current borrower, borrowing history, waitlist, and usage duration
2. WHEN clicking on a student profile THEN the system SHALL display current checkouts, past borrowings, and due dates
3. WHEN viewing item details THEN the system SHALL show donor information, availability status, and transaction history
4. WHEN viewing user details THEN the system SHALL display role-appropriate information based on viewer permissions
5. WHEN navigating between related items THEN the system SHALL provide breadcrumb navigation and quick links

### Requirement 17: Enhanced Checkout User Experience

**User Story:** As a Student, I want a smooth and intuitive checkout process so that I can quickly request items without difficulties.

#### Acceptance Criteria

1. WHEN requesting checkout THEN the system SHALL provide a streamlined single-step request process
2. WHEN viewing available items THEN the system SHALL display clear availability indicators and quick action buttons
3. WHEN applying for checkout THEN the system SHALL pre-populate user information and minimize required fields
4. WHEN checkout is requested THEN the system SHALL provide immediate confirmation and expected approval timeline
5. WHEN items are unavailable THEN the system SHALL offer one-click waitlist joining with position indication

### Requirement 18: Configurable Item Categories

**User Story:** As an Admin, I want to manage item categories dynamically so that new types of inventory can be added as needed.

#### Acceptance Criteria

1. WHEN managing categories THEN the system SHALL provide default categories (Books, Laptops, Kits)
2. WHEN adding categories THEN the system SHALL allow creation of new item types with custom attributes
3. WHEN configuring categories THEN the system SHALL support category-specific fields and validation rules
4. WHEN viewing inventory THEN the system SHALL filter and display items by their configured categories
5. WHEN deleting categories THEN the system SHALL prevent deletion if inventory items are associated

### Requirement 19: Role-Based Analytics Access

**User Story:** As a user with appropriate permissions, I want to view analytics relevant to my role so that I can make informed decisions within my scope of responsibility.

#### Acceptance Criteria

1. WHEN Admin views analytics THEN the system SHALL display comprehensive system-wide statistics and trends
2. WHEN Incharge views analytics THEN the system SHALL display department-specific usage patterns and volunteer performance
3. WHEN Volunteer views analytics THEN the system SHALL display daily transaction summaries and pending approvals
4. WHEN generating reports THEN the system SHALL filter data based on user role and department permissions
5. WHEN exporting analytics THEN the system SHALL restrict data export based on role-based access controls

### Requirement 20: Enhanced Volunteer Notifications

**User Story:** As a Volunteer, I want to receive notifications about my scheduled duties so that I can fulfill my library management responsibilities effectively.

#### Acceptance Criteria

1. WHEN volunteers are scheduled THEN the system SHALL send daily reminder notifications to assigned volunteers
2. WHEN schedule changes occur THEN the system SHALL notify affected volunteers immediately
3. WHEN library status changes THEN the system SHALL broadcast notifications to all relevant users
4. WHEN viewing notifications THEN the system SHALL display volunteer-specific alerts and pending tasks
5. WHEN volunteers are absent THEN the system SHALL allow emergency reassignment with notifications

### Requirement 21: Audit Log Visibility Controls

**User Story:** As a user with appropriate permissions, I want to access audit logs relevant to my role so that I can track activities within my scope of responsibility.

#### Acceptance Criteria

1. WHEN Admin views audit logs THEN the system SHALL display all system activities and user actions
2. WHEN Incharge views audit logs THEN the system SHALL display department-specific activities and approvals
3. WHEN accessing audit logs THEN the system SHALL filter entries based on user role and permissions
4. WHEN viewing audit entries THEN the system SHALL display timestamp, actor, action, and relevant details
5. WHEN Volunteers access logs THEN the system SHALL restrict visibility to their own actions and assigned transactions

### Requirement 22: Fine Reporting and Management

**User Story:** As an Incharge/Admin, I want to view and export reports of all pending fines so that I can track overdue dues.

#### Acceptance Criteria

1. WHEN generating reports THEN the system SHALL create per-student pending fine reports
2. WHEN viewing reports THEN the system SHALL provide aggregated overdue summary reports
3. WHEN exporting reports THEN the system SHALL support CSV/Excel export for both report types
4. WHEN clicking on a user profile THEN the system SHALL show individual fine breakdown and overdue history
5. WHEN calculating fines THEN the system SHALL maintain historical fine records even after items are returned

### Requirement 23: Overdue Notifications and Escalation

**User Story:** As a student, I want to receive immediate and repeated overdue alerts, and as an Incharge, I want to be notified of overdue cases, so that items are returned on time.

#### Acceptance Criteria

1. WHEN an item crosses due date without return THEN the system SHALL send immediate overdue notification to student
2. WHEN items become overdue THEN the system SHALL alert Incharge with overdue list for their department
3. WHEN items remain overdue THEN the system SHALL send daily reminder notifications until resolved
4. WHEN overdue notifications are sent THEN the system SHALL escalate to higher authorities after configurable threshold per department
5. WHEN viewing overdue items THEN the system SHALL display days overdue and accumulated fine amounts

### Requirement 24: Volunteer Scheduling Validation and Exceptions

**User Story:** As an Incharge, I want the system to warn me when fewer than 2 volunteers are available for a department, so I can take corrective action.

#### Acceptance Criteria

1. WHEN creating schedules THEN the system SHALL enforce 2 volunteers per department per day rule
2. WHEN fewer than 2 active volunteers exist THEN the system SHALL warn Incharge during schedule creation
3. WHEN scheduling exceptions occur THEN the system SHALL allow override but log the exception in audit log
4. WHEN volunteers are unavailable THEN the system SHALL suggest alternative volunteers from the same department
5. WHEN schedule conflicts arise THEN the system SHALL prevent double-booking and suggest alternatives

### Requirement 25: Department Auto-Linking and User Management

**User Story:** As a student, I want my branch auto-linked to the correct department during registration so that I don't have to choose manually.

#### Acceptance Criteria

1. WHEN a student registers THEN the system SHALL auto-link their branch to corresponding department
2. WHEN branch-department mapping is missing THEN the system SHALL prompt Admin to configure the mapping
3. WHEN viewing user profiles THEN the system SHALL display department affiliation based on branch
4. WHEN managing departments THEN the system SHALL prevent orphan users without department mapping
5. WHEN updating user branch THEN the system SHALL automatically update department association

### Requirement 26: Audit Log Retention and Archival

**User Story:** As an Admin, I want audit logs to be stored with a retention policy so that system storage is optimized without losing important data.

#### Acceptance Criteria

1. WHEN storing audit logs THEN the system SHALL retain logs for a minimum of 1 year by default
2. WHEN retention period expires THEN the system SHALL archive or auto-purge logs based on configuration
3. WHEN configuring retention THEN only Admin SHALL be able to modify retention policies
4. WHEN archiving logs THEN the system SHALL maintain data integrity and provide export capabilities
5. WHEN accessing historical logs THEN the system SHALL support search and filtering within retention period

### Requirement 27: Volunteer Attendance Tracking

**User Story:** As an Incharge, I want to track volunteers' check-in and check-out during duty hours so that I can monitor attendance reliability.

#### Acceptance Criteria

1. WHEN volunteers start duty THEN the system SHALL require check-in via mobile interface
2. WHEN volunteers end duty THEN the system SHALL require check-out with duty summary
3. WHEN tracking attendance THEN the system SHALL record scheduled vs actual attendance times
4. WHEN volunteers fail to check-in/out THEN the system SHALL flag early exit or no-show incidents
5. WHEN generating reports THEN the system SHALL provide attendance summaries for Incharge evaluation

### Requirement 28: Automated Library Status Management

**User Story:** As a system administrator, I want automated library closure capabilities so that the system maintains accurate status even when manual updates are missed.

#### Acceptance Criteria

1. WHEN configuring library hours THEN the system SHALL support daily auto-close at fixed end-time
2. WHEN library end-time is reached THEN the system SHALL auto-close with default closure message
3. WHEN Incharge forgets manual closure THEN the system SHALL prevent status inconsistencies
4. WHEN auto-closure occurs THEN the system SHALL allow manual override by authorized personnel
5. WHEN status changes automatically THEN the system SHALL log the automated action in audit trail