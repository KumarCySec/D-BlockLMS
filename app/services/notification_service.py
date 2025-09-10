"""
Notification service for managing user notifications
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from app import db
from app.models.notification import Notification, NotificationType, NotificationPriority
from app.models.user import User
from app.models.transaction import Transaction
from app.models.inventory_item import InventoryItem


class NotificationService:
    """Service for creating and managing notifications"""
    
    @staticmethod
    def create_notification(
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        transaction_id: Optional[int] = None,
        item_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> Notification:
        """Create a new notification"""
        notification = Notification.create_notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            transaction_id=transaction_id,
            item_id=item_id,
            data=data,
            expires_at=expires_at
        )
        
        try:
            db.session.commit()
            # TODO: Trigger notification delivery (Web Push, SMS, Email)
            NotificationService._log_notification_created(notification)
            return notification
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def _log_notification_created(notification: Notification):
        """Log notification creation for debugging"""
        from flask import current_app
        current_app.logger.info(
            f"Notification created: {notification.type.value} for user {notification.user_id}"
        )
    
    # Transaction-related notifications
    
    @staticmethod
    def notify_transaction_approved(transaction: Transaction):
        """Notify user when their checkout request is approved"""
        return NotificationService.create_notification(
            user_id=transaction.user_id,
            notification_type=NotificationType.TRANSACTION_APPROVED,
            title="Checkout Request Approved",
            message=f"Your request for '{transaction.item.title}' has been approved. Please collect it from the library.",
            priority=NotificationPriority.HIGH,
            transaction_id=transaction.id,
            item_id=transaction.item_id,
            data={
                'transaction_id': transaction.transaction_id,
                'due_date': transaction.due_date.isoformat() if transaction.due_date else None
            }
        )
    
    @staticmethod
    def notify_transaction_rejected(transaction: Transaction, reason: str = None):
        """Notify user when their checkout request is rejected"""
        message = f"Your request for '{transaction.item.title}' has been rejected."
        if reason:
            message += f" Reason: {reason}"
        
        return NotificationService.create_notification(
            user_id=transaction.user_id,
            notification_type=NotificationType.TRANSACTION_REJECTED,
            title="Checkout Request Rejected",
            message=message,
            priority=NotificationPriority.NORMAL,
            transaction_id=transaction.id,
            item_id=transaction.item_id,
            data={
                'transaction_id': transaction.transaction_id,
                'rejection_reason': reason
            }
        )
    
    @staticmethod
    def notify_transaction_issued(transaction: Transaction):
        """Notify user when item is issued to them"""
        return NotificationService.create_notification(
            user_id=transaction.user_id,
            notification_type=NotificationType.TRANSACTION_ISSUED,
            title="Item Issued",
            message=f"'{transaction.item.title}' has been issued to you. Due date: {transaction.due_date.strftime('%Y-%m-%d') if transaction.due_date else 'N/A'}",
            priority=NotificationPriority.HIGH,
            transaction_id=transaction.id,
            item_id=transaction.item_id,
            data={
                'transaction_id': transaction.transaction_id,
                'due_date': transaction.due_date.isoformat() if transaction.due_date else None
            }
        )
    
    @staticmethod
    def notify_transaction_returned(transaction: Transaction):
        """Notify user when item return is processed"""
        return NotificationService.create_notification(
            user_id=transaction.user_id,
            notification_type=NotificationType.TRANSACTION_RETURNED,
            title="Item Returned",
            message=f"Thank you for returning '{transaction.item.title}'. Transaction completed successfully.",
            priority=NotificationPriority.NORMAL,
            transaction_id=transaction.id,
            item_id=transaction.item_id,
            data={
                'transaction_id': transaction.transaction_id,
                'returned_at': transaction.returned_at.isoformat() if transaction.returned_at else None
            }
        )
    
    @staticmethod
    def notify_transaction_overdue(transaction: Transaction):
        """Notify user when their item is overdue"""
        days_overdue = transaction.days_overdue()
        return NotificationService.create_notification(
            user_id=transaction.user_id,
            notification_type=NotificationType.TRANSACTION_OVERDUE,
            title="Item Overdue",
            message=f"'{transaction.item.title}' is {days_overdue} day(s) overdue. Please return it as soon as possible to avoid additional fines.",
            priority=NotificationPriority.URGENT,
            transaction_id=transaction.id,
            item_id=transaction.item_id,
            data={
                'transaction_id': transaction.transaction_id,
                'days_overdue': days_overdue,
                'fine_amount': str(transaction.fine_accumulated)
            }
        )
    
    @staticmethod
    def notify_transaction_due_soon(transaction: Transaction, days_until_due: int = 1):
        """Notify user when their item is due soon"""
        return NotificationService.create_notification(
            user_id=transaction.user_id,
            notification_type=NotificationType.TRANSACTION_DUE_SOON,
            title="Item Due Soon",
            message=f"'{transaction.item.title}' is due in {days_until_due} day(s). Please return or renew it.",
            priority=NotificationPriority.HIGH,
            transaction_id=transaction.id,
            item_id=transaction.item_id,
            data={
                'transaction_id': transaction.transaction_id,
                'days_until_due': days_until_due,
                'due_date': transaction.due_date.isoformat() if transaction.due_date else None
            }
        )
    
    # Renewal notifications
    
    @staticmethod
    def notify_renewal_approved(transaction: Transaction):
        """Notify user when their renewal request is approved"""
        return NotificationService.create_notification(
            user_id=transaction.user_id,
            notification_type=NotificationType.RENEWAL_APPROVED,
            title="Renewal Approved",
            message=f"Your renewal request for '{transaction.item.title}' has been approved. New due date: {transaction.due_date.strftime('%Y-%m-%d') if transaction.due_date else 'N/A'}",
            priority=NotificationPriority.NORMAL,
            transaction_id=transaction.id,
            item_id=transaction.item_id,
            data={
                'transaction_id': transaction.transaction_id,
                'new_due_date': transaction.due_date.isoformat() if transaction.due_date else None,
                'renewal_count': transaction.renew_count
            }
        )
    
    @staticmethod
    def notify_renewal_rejected(transaction: Transaction, reason: str = None):
        """Notify user when their renewal request is rejected"""
        message = f"Your renewal request for '{transaction.item.title}' has been rejected."
        if reason:
            message += f" Reason: {reason}"
        
        return NotificationService.create_notification(
            user_id=transaction.user_id,
            notification_type=NotificationType.RENEWAL_REJECTED,
            title="Renewal Rejected",
            message=message,
            priority=NotificationPriority.NORMAL,
            transaction_id=transaction.id,
            item_id=transaction.item_id,
            data={
                'transaction_id': transaction.transaction_id,
                'rejection_reason': reason
            }
        )
    
    # Fine notifications
    
    @staticmethod
    def notify_fine_applied(transaction: Transaction, fine_amount: float):
        """Notify user when a fine is applied"""
        return NotificationService.create_notification(
            user_id=transaction.user_id,
            notification_type=NotificationType.FINE_APPLIED,
            title="Fine Applied",
            message=f"A fine of ₹{fine_amount:.2f} has been applied to your account for overdue item '{transaction.item.title}'.",
            priority=NotificationPriority.HIGH,
            transaction_id=transaction.id,
            item_id=transaction.item_id,
            data={
                'transaction_id': transaction.transaction_id,
                'fine_amount': fine_amount
            }
        )
    
    @staticmethod
    def notify_fine_waived(transaction: Transaction, waived_amount: float, reason: str = None):
        """Notify user when a fine is waived"""
        message = f"A fine of ₹{waived_amount:.2f} has been waived for '{transaction.item.title}'."
        if reason:
            message += f" Reason: {reason}"
        
        return NotificationService.create_notification(
            user_id=transaction.user_id,
            notification_type=NotificationType.FINE_WAIVED,
            title="Fine Waived",
            message=message,
            priority=NotificationPriority.NORMAL,
            transaction_id=transaction.id,
            item_id=transaction.item_id,
            data={
                'transaction_id': transaction.transaction_id,
                'waived_amount': waived_amount,
                'waiver_reason': reason
            }
        )
    
    # Waitlist notifications
    
    @staticmethod
    def notify_waitlist_available(user_id: int, item: InventoryItem):
        """Notify user when waitlisted item becomes available"""
        return NotificationService.create_notification(
            user_id=user_id,
            notification_type=NotificationType.WAITLIST_AVAILABLE,
            title="Waitlisted Item Available",
            message=f"'{item.title}' is now available! You have 24 hours to claim it.",
            priority=NotificationPriority.URGENT,
            item_id=item.id,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            data={
                'item_title': item.title,
                'claim_deadline': (datetime.utcnow() + timedelta(hours=24)).isoformat()
            }
        )
    
    # System notifications
    
    @staticmethod
    def notify_system_announcement(user_ids: List[int], title: str, message: str, priority: NotificationPriority = NotificationPriority.NORMAL):
        """Send system announcement to multiple users"""
        notifications = []
        for user_id in user_ids:
            notification = NotificationService.create_notification(
                user_id=user_id,
                notification_type=NotificationType.SYSTEM_ANNOUNCEMENT,
                title=title,
                message=message,
                priority=priority
            )
            notifications.append(notification)
        
        return notifications
    
    # Utility methods
    
    @staticmethod
    def get_user_notifications(user_id: int, unread_only: bool = False, limit: int = None) -> List[Notification]:
        """Get notifications for a user"""
        return Notification.get_user_notifications(user_id, unread_only, limit)
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """Get count of unread notifications for a user"""
        return Notification.get_unread_count(user_id)
    
    @staticmethod
    def mark_as_read(notification_id: int, user_id: int) -> bool:
        """Mark a specific notification as read"""
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        if notification:
            notification.mark_as_read()
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def mark_all_as_read(user_id: int) -> int:
        """Mark all notifications as read for a user"""
        count = Notification.mark_all_as_read(user_id)
        db.session.commit()
        return count
    
    @staticmethod
    def cleanup_expired_notifications() -> int:
        """Remove expired notifications"""
        count = Notification.cleanup_expired()
        db.session.commit()
        return count
    
    # Batch notification methods for scheduled tasks
    
    @staticmethod
    def send_overdue_reminders():
        """Send overdue reminders for all overdue transactions"""
        from app.models.transaction import Transaction
        overdue_transactions = Transaction.get_overdue_transactions()
        
        notifications_sent = 0
        for transaction in overdue_transactions:
            try:
                NotificationService.notify_transaction_overdue(transaction)
                notifications_sent += 1
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to send overdue notification for transaction {transaction.transaction_id}: {e}")
        
        return notifications_sent
    
    @staticmethod
    def send_due_soon_reminders(days: int = 1):
        """Send due soon reminders for transactions due within specified days"""
        from app.models.transaction import Transaction
        due_soon_transactions = Transaction.get_due_soon(days)
        
        notifications_sent = 0
        for transaction in due_soon_transactions:
            try:
                NotificationService.notify_transaction_due_soon(transaction, days)
                notifications_sent += 1
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Failed to send due soon notification for transaction {transaction.transaction_id}: {e}")
        
        return notifications_sent