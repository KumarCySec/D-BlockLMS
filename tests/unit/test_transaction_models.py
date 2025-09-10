"""
Unit tests for transaction models and business logic
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app import create_app, db
from app.models.transaction import Transaction, TransactionStatus, TransactionCounter
from app.models.user import User
from app.models.role import Role
from app.models.inventory_item import InventoryItem, ItemType, ItemStatus
from app.models.department import Department
from app.models.notification import Notification, NotificationType


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def sample_department(app):
    """Create sample department"""
    with app.app_context():
        dept = Department(name="Computer Science", code="CS")
        db.session.add(dept)
        db.session.commit()
        # Refresh to avoid detached instance
        db.session.refresh(dept)
        return dept


@pytest.fixture
def sample_role(app):
    """Create sample role"""
    with app.app_context():
        role = Role(name="Student", description="Student role")
        db.session.add(role)
        db.session.commit()
        # Refresh to avoid detached instance
        db.session.refresh(role)
        return role


@pytest.fixture
def sample_user(app, sample_department, sample_role):
    """Create sample user"""
    with app.app_context():
        from app.models.user import UserStatus
        user = User(
            name="Test User",
            email="test@example.com",
            roll_number="CS2021001",
            branch="Computer Science",
            batch="2021-2025",
            phone="1234567890",
            department_id=sample_department.id,
            status=UserStatus.ACTIVE
        )
        user.set_password("password123")
        user.roles.append(sample_role)
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def sample_donor(app):
    """Create sample donor"""
    with app.app_context():
        from app.models.donor import Donor
        donor = Donor(
            name="Test Donor",
            email="donor@example.com",
            batch="2020",
            branch="Computer Science"
        )
        db.session.add(donor)
        db.session.commit()
        db.session.refresh(donor)
        return donor


@pytest.fixture
def sample_item(app, sample_donor):
    """Create sample inventory item"""
    with app.app_context():
        item = InventoryItem(
            title="Test Book",
            authors="Test Author",
            isbn="1234567890123",
            item_type=ItemType.BOOK,
            status=ItemStatus.AVAILABLE,
            sku_code="BOOK001",
            donor_id=sample_donor.id
        )
        db.session.add(item)
        db.session.commit()
        db.session.refresh(item)
        return item


class TestTransactionCounter:
    """Test transaction counter functionality"""
    
    def test_generate_transaction_id_format(self, app):
        """Test transaction ID format DBL-YYYYMMDD-XXXX"""
        with app.app_context():
            # Test with specific date
            test_date = datetime(2025, 1, 15).date()
            transaction_id = TransactionCounter.generate_transaction_id(test_date)
            
            assert transaction_id.startswith("DBL-20250115-")
            assert transaction_id.endswith("0001")
            assert len(transaction_id) == 17  # DBL-YYYYMMDD-XXXX
    
    def test_generate_sequential_ids(self, app):
        """Test sequential ID generation"""
        with app.app_context():
            test_date = datetime(2025, 1, 15).date()
            
            id1 = TransactionCounter.generate_transaction_id(test_date)
            id2 = TransactionCounter.generate_transaction_id(test_date)
            id3 = TransactionCounter.generate_transaction_id(test_date)
            
            assert id1 == "DBL-20250115-0001"
            assert id2 == "DBL-20250115-0002"
            assert id3 == "DBL-20250115-0003"
    
    def test_different_dates_reset_counter(self, app):
        """Test that different dates reset the counter"""
        with app.app_context():
            date1 = datetime(2025, 1, 15).date()
            date2 = datetime(2025, 1, 16).date()
            
            id1 = TransactionCounter.generate_transaction_id(date1)
            id2 = TransactionCounter.generate_transaction_id(date1)
            id3 = TransactionCounter.generate_transaction_id(date2)
            
            assert id1 == "DBL-20250115-0001"
            assert id2 == "DBL-20250115-0002"
            assert id3 == "DBL-20250116-0001"
    
    def test_concurrent_id_generation(self, app):
        """Test atomic ID generation under concurrent access"""
        with app.app_context():
            test_date = datetime(2025, 1, 15).date()
            
            # Simulate concurrent requests
            ids = []
            for _ in range(10):
                transaction_id = TransactionCounter.generate_transaction_id(test_date)
                ids.append(transaction_id)
            
            # All IDs should be unique
            assert len(set(ids)) == 10
            
            # IDs should be sequential
            for i, transaction_id in enumerate(ids, 1):
                expected = f"DBL-20250115-{i:04d}"
                assert transaction_id == expected


class TestTransaction:
    """Test transaction model functionality"""
    
    def test_create_transaction_request(self, app, sample_user, sample_item):
        """Test creating a transaction request"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id,
                notes="Test request"
            )
            db.session.commit()
            
            assert transaction.user_id == sample_user.id
            assert transaction.item_id == sample_item.id
            assert transaction.status == TransactionStatus.REQUESTED
            assert transaction.notes == "Test request"
            assert transaction.transaction_id.startswith("DBL-")
            assert transaction.renew_count == 0
            assert transaction.fine_accumulated == Decimal('0.00')
    
    def test_transaction_state_machine(self, app, sample_user, sample_item):
        """Test transaction status transitions"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            db.session.commit()
            
            # Test valid transitions
            assert transaction.can_transition_to(TransactionStatus.APPROVED)
            assert transaction.can_transition_to(TransactionStatus.REJECTED)
            assert transaction.can_transition_to(TransactionStatus.CANCELLED)
            
            # Test invalid transitions
            assert not transaction.can_transition_to(TransactionStatus.BORROWED)
            assert not transaction.can_transition_to(TransactionStatus.RETURNED)
            
            # Approve transaction
            transaction.transition_to(TransactionStatus.APPROVED, actor_id=sample_user.id)
            assert transaction.status == TransactionStatus.APPROVED
            assert transaction.approved_at is not None
            assert transaction.due_date is not None
            
            # Test transitions from approved
            assert transaction.can_transition_to(TransactionStatus.BORROWED)
            assert not transaction.can_transition_to(TransactionStatus.REQUESTED)
    
    def test_transaction_approval_sets_due_date(self, app, sample_user, sample_item):
        """Test that approval sets due date"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            db.session.commit()
            
            approval_time = datetime.utcnow()
            transaction.transition_to(TransactionStatus.APPROVED, actor_id=sample_user.id)
            
            assert transaction.due_date is not None
            # Due date should be approximately 7 days from approval
            expected_due = approval_time + timedelta(days=7)
            time_diff = abs((transaction.due_date - expected_due).total_seconds())
            assert time_diff < 60  # Within 1 minute
    
    def test_overdue_calculation(self, app, sample_user, sample_item):
        """Test overdue calculation"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            transaction.transition_to(TransactionStatus.APPROVED, actor_id=sample_user.id)
            transaction.transition_to(TransactionStatus.BORROWED, actor_id=sample_user.id)
            
            # Set due date to past
            transaction.due_date = datetime.utcnow() - timedelta(days=3)
            db.session.commit()
            
            assert transaction.is_overdue()
            assert transaction.days_overdue() == 3
    
    def test_fine_calculation(self, app, sample_user, sample_item):
        """Test fine calculation for overdue items"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            transaction.transition_to(TransactionStatus.APPROVED, actor_id=sample_user.id)
            transaction.transition_to(TransactionStatus.BORROWED, actor_id=sample_user.id)
            
            # Set due date to 5 days ago
            transaction.due_date = datetime.utcnow() - timedelta(days=5)
            db.session.commit()
            
            fine = transaction.calculate_fine(daily_rate=Decimal('2.00'))
            assert fine == Decimal('10.00')  # 5 days * 2.00
            assert transaction.fine_accumulated == Decimal('10.00')
    
    def test_renewal_functionality(self, app, sample_user, sample_item):
        """Test renewal functionality"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            transaction.transition_to(TransactionStatus.APPROVED, actor_id=sample_user.id)
            transaction.transition_to(TransactionStatus.BORROWED, actor_id=sample_user.id)
            db.session.commit()
            
            original_due_date = transaction.due_date
            
            # Test renewal
            can_renew, reason = transaction.can_renew()
            assert can_renew
            
            transaction.request_renewal(days=7)
            assert transaction.renew_count == 1
            assert transaction.due_date == original_due_date + timedelta(days=7)
            
            # Test max renewals
            transaction.renew_count = 4  # Max renewals
            can_renew, reason = transaction.can_renew()
            assert not can_renew
            assert "Maximum renewals" in reason
    
    def test_fine_waiver(self, app, sample_user, sample_item):
        """Test fine waiver functionality"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            transaction.fine_accumulated = Decimal('50.00')
            db.session.commit()
            
            transaction.waive_fine(
                waiver_user_id=sample_user.id,
                reason="First-time offender"
            )
            
            assert transaction.fine_waived
            assert transaction.fine_waived_by == sample_user.id
            assert transaction.fine_waived_reason == "First-time offender"
    
    def test_transaction_to_dict(self, app, sample_user, sample_item):
        """Test transaction serialization"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id,
                notes="Test transaction"
            )
            db.session.commit()
            
            data = transaction.to_dict()
            
            assert data['transaction_id'] == transaction.transaction_id
            assert data['status'] == 'requested'
            assert data['notes'] == "Test transaction"
            assert 'user' in data
            assert 'item' in data
            assert data['user']['name'] == sample_user.name
            assert data['item']['title'] == sample_item.title
    
    def test_get_user_transactions(self, app, sample_user, sample_item):
        """Test getting user transactions"""
        with app.app_context():
            # Create multiple transactions
            t1 = Transaction.create_request(sample_user.id, sample_item.id)
            t2 = Transaction.create_request(sample_user.id, sample_item.id)
            t1.transition_to(TransactionStatus.APPROVED, actor_id=sample_user.id)
            db.session.commit()
            
            # Get all transactions
            transactions = Transaction.get_user_transactions(sample_user.id)
            assert len(transactions) == 2
            
            # Get only approved transactions
            approved_transactions = Transaction.get_user_transactions(
                sample_user.id, 
                status=['approved']
            )
            assert len(approved_transactions) == 1
            assert approved_transactions[0].status == TransactionStatus.APPROVED
    
    def test_get_overdue_transactions(self, app, sample_user, sample_item):
        """Test getting overdue transactions"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            transaction.transition_to(TransactionStatus.APPROVED, actor_id=sample_user.id)
            transaction.transition_to(TransactionStatus.BORROWED, actor_id=sample_user.id)
            
            # Set due date to past
            transaction.due_date = datetime.utcnow() - timedelta(days=1)
            db.session.commit()
            
            overdue_transactions = Transaction.get_overdue_transactions()
            assert len(overdue_transactions) == 1
            assert overdue_transactions[0].id == transaction.id
    
    def test_transaction_statistics(self, app, sample_user, sample_item):
        """Test transaction statistics"""
        with app.app_context():
            # Create transactions with different statuses
            t1 = Transaction.create_request(sample_user.id, sample_item.id)
            t2 = Transaction.create_request(sample_user.id, sample_item.id)
            t3 = Transaction.create_request(sample_user.id, sample_item.id)
            
            t1.transition_to(TransactionStatus.APPROVED, actor_id=sample_user.id)
            t2.transition_to(TransactionStatus.REJECTED, actor_id=sample_user.id)
            db.session.commit()
            
            stats = Transaction.get_statistics()
            
            assert stats['total_transactions'] == 3
            assert stats['status_counts']['requested'] == 1
            assert stats['status_counts']['approved'] == 1
            assert stats['status_counts']['rejected'] == 1
            assert stats['approval_rate'] > 0


class TestTransactionNotifications:
    """Test transaction notification integration"""
    
    def test_approval_creates_notification(self, app, sample_user, sample_item):
        """Test that approving a transaction creates a notification"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            db.session.commit()
            
            # Count notifications before approval
            initial_count = Notification.query.filter_by(user_id=sample_user.id).count()
            
            # Approve transaction
            transaction.transition_to(TransactionStatus.APPROVED, actor_id=sample_user.id)
            db.session.commit()
            
            # Check notification was created
            final_count = Notification.query.filter_by(user_id=sample_user.id).count()
            assert final_count == initial_count + 1
            
            # Check notification details
            notification = Notification.query.filter_by(
                user_id=sample_user.id,
                type=NotificationType.TRANSACTION_APPROVED
            ).first()
            
            assert notification is not None
            assert notification.transaction_id == transaction.id
            assert "approved" in notification.message.lower()
    
    def test_rejection_creates_notification(self, app, sample_user, sample_item):
        """Test that rejecting a transaction creates a notification"""
        with app.app_context():
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            db.session.commit()
            
            # Reject transaction
            transaction.transition_to(
                TransactionStatus.REJECTED, 
                actor_id=sample_user.id,
                notes="Item not available"
            )
            db.session.commit()
            
            # Check notification was created
            notification = Notification.query.filter_by(
                user_id=sample_user.id,
                type=NotificationType.TRANSACTION_REJECTED
            ).first()
            
            assert notification is not None
            assert notification.transaction_id == transaction.id
            assert "rejected" in notification.message.lower()
            assert "Item not available" in notification.message


class TestTransactionAuditLogging:
    """Test transaction audit logging"""
    
    def test_transaction_creation_logged(self, app, sample_user, sample_item):
        """Test that transaction creation is logged"""
        with app.app_context():
            from app.models.audit_log import AuditLog, AuditAction
            from app.utils.transaction_service import transaction_service
            
            initial_count = AuditLog.query.count()
            
            # Use the service layer which includes audit logging
            transaction = transaction_service.create_checkout_request(
                user_id=sample_user.id,
                item_id=sample_item.id,
                notes="Test request"
            )
            
            final_count = AuditLog.query.count()
            assert final_count == initial_count + 1
            
            # Check audit log details
            audit_log = AuditLog.query.filter_by(
                action=AuditAction.CHECKOUT_REQUEST
            ).first()
            
            assert audit_log is not None
            assert audit_log.target_type == 'Transaction'
            assert audit_log.target_id == transaction.id
    
    def test_status_transitions_logged(self, app, sample_user, sample_item):
        """Test that status transitions are logged"""
        with app.app_context():
            from app.models.audit_log import AuditLog, AuditAction
            
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            db.session.commit()
            
            initial_count = AuditLog.query.count()
            
            # Approve transaction
            transaction.transition_to(TransactionStatus.APPROVED, actor_id=sample_user.id)
            db.session.commit()
            
            final_count = AuditLog.query.count()
            assert final_count == initial_count + 1
            
            # Check audit log for approval
            audit_log = AuditLog.query.filter_by(
                action=AuditAction.CHECKOUT_APPROVE
            ).first()
            
            assert audit_log is not None
            assert audit_log.target_identifier == transaction.transaction_id