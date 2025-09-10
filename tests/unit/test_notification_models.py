"""
Unit tests for notification models and service
"""
import pytest
from datetime import datetime, timedelta
from app import create_app, db
from app.models.notification import Notification, NotificationType, NotificationPriority
from app.models.user import User
from app.models.role import Role
from app.models.inventory_item import InventoryItem, ItemType, ItemStatus
from app.models.transaction import Transaction, TransactionStatus
from app.models.department import Department
from app.services.notification_service import NotificationService


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def sample_department(app):
    """Create sample department"""
    with app.app_context():
        dept = Department(name="Computer Science", code="CS")
        db.session.add(dept)
        db.session.commit()
        db.session.refresh(dept)
        return dept


@pytest.fixture
def sample_role(app):
    """Create sample role"""
    with app.app_context():
        role = Role(name="Student", description="Student role")
        db.session.add(role)
        db.session.commit()
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


@pytest.fixture
def sample_transaction(app, sample_user, sample_item):
    """Create sample transaction"""
    with app.app_context():
        transaction = Transaction.create_request(
            user_id=sample_user.id,
            item_id=sample_item.id,
            notes="Test transaction"
        )
        db.session.commit()
        return transaction


class TestNotificationModel:
    """Test notification model functionality"""
    
    def test_create_notification(self, app, sample_user):
        """Test creating a notification"""
        with app.app_context():
            notification = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                title="Test Notification",
                message="This is a test notification",
                priority=NotificationPriority.NORMAL
            )
            
            assert notification.user_id == sample_user.id
            assert notification.type == NotificationType.SYSTEM_ANNOUNCEMENT
            assert notification.title == "Test Notification"
            assert notification.message == "This is a test notification"
            assert notification.priority == NotificationPriority.NORMAL
            assert not notification.is_read
            assert not notification.is_sent
    
    def test_notification_with_expiration(self, app, sample_user):
        """Test notification with expiration date"""
        with app.app_context():
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            notification = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.WAITLIST_AVAILABLE,
                title="Item Available",
                message="Your waitlisted item is available",
                expires_at=expires_at
            )
            
            assert notification.expires_at == expires_at
            assert not notification.is_expired()
            
            # Test expired notification
            notification.expires_at = datetime.utcnow() - timedelta(hours=1)
            assert notification.is_expired()
    
    def test_mark_as_read(self, app, sample_user):
        """Test marking notification as read"""
        with app.app_context():
            notification = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                title="Test",
                message="Test message"
            )
            
            assert not notification.is_read
            assert notification.read_at is None
            
            notification.mark_as_read()
            
            assert notification.is_read
            assert notification.read_at is not None
    
    def test_mark_as_sent(self, app, sample_user):
        """Test marking notification as sent"""
        with app.app_context():
            notification = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                title="Test",
                message="Test message"
            )
            
            assert not notification.is_sent
            assert notification.sent_at is None
            
            notification.mark_as_sent(delivery_method="email")
            
            assert notification.is_sent
            assert notification.sent_at is not None
            assert notification.delivery_method == "email"
    
    def test_notification_to_dict(self, app, sample_user, sample_transaction):
        """Test notification serialization"""
        with app.app_context():
            notification = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.TRANSACTION_APPROVED,
                title="Transaction Approved",
                message="Your request has been approved",
                transaction_id=sample_transaction.id,
                item_id=sample_transaction.item_id,
                data={"custom_field": "custom_value"}
            )
            
            data = notification.to_dict(include_user=True)
            
            assert data['type'] == 'transaction_approved'
            assert data['title'] == "Transaction Approved"
            assert data['message'] == "Your request has been approved"
            assert data['data']['custom_field'] == "custom_value"
            assert 'user' in data
            assert data['user']['name'] == sample_user.name
            assert 'transaction_id' in data
            assert 'item' in data
    
    def test_get_user_notifications(self, app, sample_user):
        """Test getting user notifications"""
        with app.app_context():
            # Create multiple notifications
            n1 = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                title="First",
                message="First message"
            )
            
            n2 = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.TRANSACTION_APPROVED,
                title="Second",
                message="Second message"
            )
            
            n2.mark_as_read()
            db.session.commit()
            
            # Get all notifications
            all_notifications = Notification.get_user_notifications(sample_user.id)
            assert len(all_notifications) == 2
            
            # Get only unread notifications
            unread_notifications = Notification.get_user_notifications(
                sample_user.id, 
                unread_only=True
            )
            assert len(unread_notifications) == 1
            assert unread_notifications[0].id == n1.id
    
    def test_get_unread_count(self, app, sample_user):
        """Test getting unread notification count"""
        with app.app_context():
            # Initially no notifications
            assert Notification.get_unread_count(sample_user.id) == 0
            
            # Create notifications
            n1 = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                title="First",
                message="First message"
            )
            
            n2 = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.TRANSACTION_APPROVED,
                title="Second",
                message="Second message"
            )
            
            assert Notification.get_unread_count(sample_user.id) == 2
            
            # Mark one as read
            n1.mark_as_read()
            db.session.commit()
            
            assert Notification.get_unread_count(sample_user.id) == 1
    
    def test_mark_all_as_read(self, app, sample_user):
        """Test marking all notifications as read"""
        with app.app_context():
            # Create multiple notifications
            for i in range(3):
                Notification.create_notification(
                    user_id=sample_user.id,
                    notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                    title=f"Notification {i}",
                    message=f"Message {i}"
                )
            
            assert Notification.get_unread_count(sample_user.id) == 3
            
            # Mark all as read
            marked_count = Notification.mark_all_as_read(sample_user.id)
            db.session.commit()
            
            assert marked_count == 3
            assert Notification.get_unread_count(sample_user.id) == 0
    
    def test_cleanup_expired(self, app, sample_user):
        """Test cleaning up expired notifications"""
        with app.app_context():
            # Create expired notification
            expired_notification = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.WAITLIST_AVAILABLE,
                title="Expired",
                message="This should be cleaned up",
                expires_at=datetime.utcnow() - timedelta(hours=1)
            )
            
            # Create non-expired notification
            active_notification = Notification.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                title="Active",
                message="This should remain"
            )
            
            db.session.commit()
            
            # Cleanup expired notifications
            cleaned_count = Notification.cleanup_expired()
            db.session.commit()
            
            assert cleaned_count == 1
            
            # Check that only active notification remains
            remaining_notifications = Notification.query.all()
            assert len(remaining_notifications) == 1
            assert remaining_notifications[0].id == active_notification.id


class TestNotificationService:
    """Test notification service functionality"""
    
    def test_create_notification_service(self, app, sample_user):
        """Test creating notification through service"""
        with app.app_context():
            notification = NotificationService.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                title="Service Test",
                message="Created through service",
                priority=NotificationPriority.HIGH
            )
            
            assert notification.user_id == sample_user.id
            assert notification.title == "Service Test"
            assert notification.priority == NotificationPriority.HIGH
    
    def test_transaction_approval_notification(self, app, sample_transaction):
        """Test transaction approval notification"""
        with app.app_context():
            notification = NotificationService.notify_transaction_approved(sample_transaction)
            
            assert notification.user_id == sample_transaction.user_id
            assert notification.type == NotificationType.TRANSACTION_APPROVED
            assert notification.transaction_id == sample_transaction.id
            assert notification.item_id == sample_transaction.item_id
            assert "approved" in notification.message.lower()
            assert notification.priority == NotificationPriority.HIGH
    
    def test_transaction_rejection_notification(self, app, sample_transaction):
        """Test transaction rejection notification"""
        with app.app_context():
            reason = "Item not available"
            notification = NotificationService.notify_transaction_rejected(
                sample_transaction, 
                reason
            )
            
            assert notification.user_id == sample_transaction.user_id
            assert notification.type == NotificationType.TRANSACTION_REJECTED
            assert notification.transaction_id == sample_transaction.id
            assert "rejected" in notification.message.lower()
            assert reason in notification.message
    
    def test_transaction_issued_notification(self, app, sample_transaction):
        """Test transaction issued notification"""
        with app.app_context():
            # Set up transaction as approved with due date
            sample_transaction.transition_to(
                TransactionStatus.APPROVED, 
                actor_id=sample_transaction.user_id
            )
            db.session.commit()
            
            notification = NotificationService.notify_transaction_issued(sample_transaction)
            
            assert notification.user_id == sample_transaction.user_id
            assert notification.type == NotificationType.TRANSACTION_ISSUED
            assert "issued" in notification.message.lower()
            assert notification.priority == NotificationPriority.HIGH
    
    def test_overdue_notification(self, app, sample_transaction):
        """Test overdue notification"""
        with app.app_context():
            # Set up overdue transaction
            sample_transaction.transition_to(
                TransactionStatus.APPROVED, 
                actor_id=sample_transaction.user_id
            )
            sample_transaction.transition_to(
                TransactionStatus.BORROWED, 
                actor_id=sample_transaction.user_id
            )
            sample_transaction.due_date = datetime.utcnow() - timedelta(days=3)
            db.session.commit()
            
            notification = NotificationService.notify_transaction_overdue(sample_transaction)
            
            assert notification.user_id == sample_transaction.user_id
            assert notification.type == NotificationType.TRANSACTION_OVERDUE
            assert "overdue" in notification.message.lower()
            assert "3 day" in notification.message
            assert notification.priority == NotificationPriority.URGENT
    
    def test_due_soon_notification(self, app, sample_transaction):
        """Test due soon notification"""
        with app.app_context():
            # Set up transaction due soon
            sample_transaction.transition_to(
                TransactionStatus.APPROVED, 
                actor_id=sample_transaction.user_id
            )
            sample_transaction.transition_to(
                TransactionStatus.BORROWED, 
                actor_id=sample_transaction.user_id
            )
            sample_transaction.due_date = datetime.utcnow() + timedelta(days=1)
            db.session.commit()
            
            notification = NotificationService.notify_transaction_due_soon(
                sample_transaction, 
                days_until_due=1
            )
            
            assert notification.user_id == sample_transaction.user_id
            assert notification.type == NotificationType.TRANSACTION_DUE_SOON
            assert "due in 1 day" in notification.message.lower()
            assert notification.priority == NotificationPriority.HIGH
    
    def test_renewal_notifications(self, app, sample_transaction):
        """Test renewal approval and rejection notifications"""
        with app.app_context():
            # Test renewal approved
            notification = NotificationService.notify_renewal_approved(sample_transaction)
            
            assert notification.type == NotificationType.RENEWAL_APPROVED
            assert "renewal" in notification.message.lower()
            assert "approved" in notification.message.lower()
            
            # Test renewal rejected
            reason = "Item has waitlist"
            notification = NotificationService.notify_renewal_rejected(
                sample_transaction, 
                reason
            )
            
            assert notification.type == NotificationType.RENEWAL_REJECTED
            assert "renewal" in notification.message.lower()
            assert "rejected" in notification.message.lower()
            assert reason in notification.message
    
    def test_fine_notifications(self, app, sample_transaction):
        """Test fine-related notifications"""
        with app.app_context():
            # Test fine applied
            fine_amount = 25.50
            notification = NotificationService.notify_fine_applied(
                sample_transaction, 
                fine_amount
            )
            
            assert notification.type == NotificationType.FINE_APPLIED
            assert "fine" in notification.message.lower()
            assert "₹25.50" in notification.message
            assert notification.priority == NotificationPriority.HIGH
            
            # Test fine waived
            waived_amount = 25.50
            reason = "First-time offender"
            notification = NotificationService.notify_fine_waived(
                sample_transaction, 
                waived_amount, 
                reason
            )
            
            assert notification.type == NotificationType.FINE_WAIVED
            assert "waived" in notification.message.lower()
            assert reason in notification.message
    
    def test_waitlist_available_notification(self, app, sample_user, sample_item):
        """Test waitlist available notification"""
        with app.app_context():
            notification = NotificationService.notify_waitlist_available(
                sample_user.id, 
                sample_item
            )
            
            assert notification.user_id == sample_user.id
            assert notification.type == NotificationType.WAITLIST_AVAILABLE
            assert notification.item_id == sample_item.id
            assert "available" in notification.message.lower()
            assert "24 hours" in notification.message
            assert notification.priority == NotificationPriority.URGENT
            assert notification.expires_at is not None
    
    def test_system_announcement(self, app, sample_user):
        """Test system announcement to multiple users"""
        with app.app_context():
            # Create another user
            user2 = User(
                name="User 2",
                email="user2@example.com",
                roll_number="CS2021002",
                branch="Computer Science",
                batch="2021-2025",
                department_id=sample_user.department_id,
                is_approved=True
            )
            db.session.add(user2)
            db.session.commit()
            
            user_ids = [sample_user.id, user2.id]
            title = "System Maintenance"
            message = "System will be down for maintenance"
            
            notifications = NotificationService.notify_system_announcement(
                user_ids, 
                title, 
                message, 
                NotificationPriority.HIGH
            )
            
            assert len(notifications) == 2
            for notification in notifications:
                assert notification.type == NotificationType.SYSTEM_ANNOUNCEMENT
                assert notification.title == title
                assert notification.message == message
                assert notification.priority == NotificationPriority.HIGH
    
    def test_service_utility_methods(self, app, sample_user):
        """Test notification service utility methods"""
        with app.app_context():
            # Create notifications
            n1 = NotificationService.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                title="Test 1",
                message="Message 1"
            )
            
            n2 = NotificationService.create_notification(
                user_id=sample_user.id,
                notification_type=NotificationType.TRANSACTION_APPROVED,
                title="Test 2",
                message="Message 2"
            )
            
            # Test get user notifications
            notifications = NotificationService.get_user_notifications(sample_user.id)
            assert len(notifications) == 2
            
            # Test get unread count
            unread_count = NotificationService.get_unread_count(sample_user.id)
            assert unread_count == 2
            
            # Test mark as read
            success = NotificationService.mark_as_read(n1.id, sample_user.id)
            assert success
            
            unread_count = NotificationService.get_unread_count(sample_user.id)
            assert unread_count == 1
            
            # Test mark all as read
            marked_count = NotificationService.mark_all_as_read(sample_user.id)
            assert marked_count == 1
            
            unread_count = NotificationService.get_unread_count(sample_user.id)
            assert unread_count == 0
    
    def test_batch_notification_methods(self, app, sample_user, sample_item):
        """Test batch notification methods"""
        with app.app_context():
            # Create overdue transaction
            transaction = Transaction.create_request(
                user_id=sample_user.id,
                item_id=sample_item.id
            )
            transaction.transition_to(
                TransactionStatus.APPROVED, 
                actor_id=sample_user.id
            )
            transaction.transition_to(
                TransactionStatus.BORROWED, 
                actor_id=sample_user.id
            )
            transaction.due_date = datetime.utcnow() - timedelta(days=1)
            db.session.commit()
            
            # Test send overdue reminders
            sent_count = NotificationService.send_overdue_reminders()
            assert sent_count == 1
            
            # Check notification was created
            notification = Notification.query.filter_by(
                user_id=sample_user.id,
                type=NotificationType.TRANSACTION_OVERDUE
            ).first()
            assert notification is not None
            
            # Test send due soon reminders
            transaction.due_date = datetime.utcnow() + timedelta(hours=12)
            db.session.commit()
            
            sent_count = NotificationService.send_due_soon_reminders(days=1)
            assert sent_count == 1
            
            # Check notification was created
            notification = Notification.query.filter_by(
                user_id=sample_user.id,
                type=NotificationType.TRANSACTION_DUE_SOON
            ).first()
            assert notification is not None