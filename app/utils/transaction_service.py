"""
Transaction Service for atomic checkout/return operations
"""
from datetime import datetime, timedelta
from decimal import Decimal
from flask import current_app
from sqlalchemy.exc import IntegrityError
from app import db
from app.models.transaction import Transaction, TransactionStatus, TransactionCounter
from app.models.inventory_item import InventoryItem
from app.models.user import User
from app.utils.audit import audit_action


class TransactionService:
    """Service class for managing transaction operations atomically"""
    
    @staticmethod
    def create_checkout_request(user_id, item_id, notes=None):
        """
        Create a new checkout request with atomic validation
        
        Args:
            user_id: ID of the requesting user
            item_id: ID of the inventory item
            notes: Optional notes for the request
            
        Returns:
            Transaction: Created transaction object
            
        Raises:
            ValueError: If validation fails
            IntegrityError: If database constraints are violated
        """
        try:
            # Validate user exists and is active
            user = User.query.get(user_id)
            if not user:
                raise ValueError("User not found")
            
            if not user.is_active_user():
                raise ValueError("User account is not active")
            
            # Validate item exists and is available
            item = InventoryItem.query.get(item_id)
            if not item:
                raise ValueError("Item not found")
            
            if not item.is_available():
                raise ValueError("Item is not available for checkout")
            
            # Check if user already has pending/active request for this item
            existing_request = Transaction.query.filter_by(
                user_id=user_id,
                item_id=item_id
            ).filter(
                Transaction.status.in_([
                    TransactionStatus.REQUESTED,
                    TransactionStatus.APPROVED,
                    TransactionStatus.BORROWED
                ])
            ).first()
            
            if existing_request:
                raise ValueError("User already has an active request for this item")
            
            # Create the transaction
            transaction = Transaction.create_request(user_id, item_id, notes)
            db.session.add(transaction)
            db.session.commit()
            
            # Log the request creation after commit
            from app.models.audit_log import AuditLog, AuditAction
            AuditLog.log_action(
                action=AuditAction.CHECKOUT_REQUEST,
                description=f"Checkout request created: {transaction.transaction_id}",
                target_type='Transaction',
                target_id=transaction.id,
                target_identifier=transaction.transaction_id,
                metadata={
                    'transaction_id': transaction.transaction_id,
                    'item_id': item_id,
                    'notes': notes,
                    'user_id': user_id
                }
            )
            
            current_app.logger.info(f"Checkout request created: {transaction.transaction_id}")
            return transaction
                
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Database integrity error in checkout request: {e}")
            raise ValueError("Failed to create checkout request due to data conflict")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating checkout request: {e}")
            raise
    
    @staticmethod
    def approve_request(transaction_id, approver_id, notes=None):
        """
        Approve a checkout request with atomic inventory update
        
        Args:
            transaction_id: ID of the transaction to approve
            approver_id: ID of the approving user
            notes: Optional approval notes
            
        Returns:
            Transaction: Updated transaction object
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Get transaction
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                raise ValueError("Transaction not found")
            
            # Validate approver permissions
            approver = User.query.get(approver_id)
            if not approver or not approver.can_approve_transactions():
                raise ValueError("User does not have approval permissions")
            
            # Validate transaction state
            if transaction.status != TransactionStatus.REQUESTED:
                raise ValueError(f"Cannot approve transaction in {transaction.status.value} status")
            
            # Get item for atomic quantity update
            item = InventoryItem.query.get(transaction.item_id)
            if not item:
                raise ValueError("Item not found")
            
            # Check availability again (atomic check)
            if not item.is_available():
                raise ValueError("Item is no longer available")
            
            # Atomically update item availability
            item.update_availability(-1)
            
            # Update transaction status
            transaction.transition_to(TransactionStatus.APPROVED, approver_id, notes)
            
            db.session.commit()
            
            current_app.logger.info(f"Transaction approved: {transaction.transaction_id}")
            
            # Send notification (async)
            try:
                from app.models.notification import Notification, NotificationType
                item = InventoryItem.query.get(transaction.item_id)
                if item:
                    Notification.create_notification(
                        user_id=transaction.user_id,
                        notification_type=NotificationType.TRANSACTION_APPROVED,
                        title="Request Approved",
                        message=f"Your request for '{item.title}' has been approved. Please collect it from the library.",
                        transaction_id=transaction.id
                    )
            except Exception as e:
                current_app.logger.warning(f"Failed to send approval notification: {e}")
            
            return transaction
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error approving transaction: {e}")
            raise
    
    @staticmethod
    def reject_request(transaction_id, approver_id, reason=None):
        """
        Reject a checkout request
        
        Args:
            transaction_id: ID of the transaction to reject
            approver_id: ID of the rejecting user
            reason: Rejection reason
            
        Returns:
            Transaction: Updated transaction object
        """
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                raise ValueError("Transaction not found")
            
            # Validate approver permissions
            approver = User.query.get(approver_id)
            if not approver or not approver.can_approve_transactions():
                raise ValueError("User does not have approval permissions")
            
            # Validate transaction state
            if transaction.status != TransactionStatus.REQUESTED:
                raise ValueError(f"Cannot reject transaction in {transaction.status.value} status")
            
            # Update transaction status
            transaction.transition_to(TransactionStatus.REJECTED, approver_id, reason)
            
            db.session.commit()
            
            current_app.logger.info(f"Transaction rejected: {transaction.transaction_id}")
            
            # Send notification (async)
            try:
                from app.models.notification import Notification, NotificationType
                item = InventoryItem.query.get(transaction.item_id)
                if item:
                    message = f"Your request for '{item.title}' has been rejected."
                    if reason:
                        message += f" Reason: {reason}"
                    Notification.create_notification(
                        user_id=transaction.user_id,
                        notification_type=NotificationType.TRANSACTION_REJECTED,
                        title="Request Rejected",
                        message=message,
                        transaction_id=transaction.id
                    )
            except Exception as e:
                current_app.logger.warning(f"Failed to send rejection notification: {e}")
            
            return transaction
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error rejecting transaction: {e}")
            raise
    
    @staticmethod
    def issue_item(transaction_id, issuer_id):
        """
        Mark item as issued (borrowed status)
        
        Args:
            transaction_id: ID of the approved transaction
            issuer_id: ID of the user issuing the item
            
        Returns:
            Transaction: Updated transaction object
        """
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                raise ValueError("Transaction not found")
            
            # Validate issuer permissions
            issuer = User.query.get(issuer_id)
            if not issuer or not issuer.can_approve_transactions():
                raise ValueError("User does not have issuing permissions")
            
            # Validate transaction state
            if transaction.status != TransactionStatus.APPROVED:
                raise ValueError(f"Cannot issue item for transaction in {transaction.status.value} status")
            
            # Update transaction status
            transaction.transition_to(TransactionStatus.BORROWED, issuer_id)
            
            db.session.commit()
            
            current_app.logger.info(f"Item issued: {transaction.transaction_id}")
            return transaction
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error issuing item: {e}")
            raise
    
    @staticmethod
    def process_return(transaction_id, processor_id, notes=None):
        """
        Process item return with atomic inventory update
        
        Args:
            transaction_id: ID of the transaction to return
            processor_id: ID of the user processing the return
            notes: Optional return notes
            
        Returns:
            Transaction: Updated transaction object
        """
        try:
            # Get transaction
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                raise ValueError("Transaction not found")
            
            # Validate processor permissions
            processor = User.query.get(processor_id)
            if not processor or not processor.can_approve_transactions():
                raise ValueError("User does not have return processing permissions")
            
            # Validate transaction state
            if transaction.status not in [TransactionStatus.BORROWED, TransactionStatus.OVERDUE]:
                raise ValueError(f"Cannot return item for transaction in {transaction.status.value} status")
            
            # Get item for atomic quantity update
            item = InventoryItem.query.get(transaction.item_id)
            if not item:
                raise ValueError("Item not found")
            
            # Calculate final fine if overdue
            if transaction.is_overdue():
                fine_config = current_app.config.get('FINE_DAILY_RATE', Decimal('1.00'))
                transaction.calculate_fine(fine_config)
            
            # Atomically update item availability
            item.update_availability(1)
            
            # Update transaction status
            transaction.transition_to(TransactionStatus.RETURNED, processor_id, notes)
            
            db.session.commit()
            
            current_app.logger.info(f"Item returned: {transaction.transaction_id}")
            
            # Notify waitlist if applicable
            try:
                from app.utils.waitlist_service import waitlist_service
                waitlist_service.notify_next_in_queue(item.id)
            except Exception as e:
                current_app.logger.warning(f"Failed to notify waitlist: {e}")
            
            return transaction
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error processing return: {e}")
            raise
    
    @staticmethod
    def cancel_request(transaction_id, user_id, reason=None):
        """
        Cancel a pending request
        
        Args:
            transaction_id: ID of the transaction to cancel
            user_id: ID of the user cancelling (must be requester or authorized)
            reason: Cancellation reason
            
        Returns:
            Transaction: Updated transaction object
        """
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                raise ValueError("Transaction not found")
            
            # Validate cancellation permissions
            user = User.query.get(user_id)
            if not user:
                raise ValueError("User not found")
            
            # Only requester or authorized personnel can cancel
            if transaction.user_id != user_id and not user.can_approve_transactions():
                raise ValueError("User does not have permission to cancel this transaction")
            
            # Validate transaction state
            if transaction.status not in [TransactionStatus.REQUESTED, TransactionStatus.APPROVED]:
                raise ValueError(f"Cannot cancel transaction in {transaction.status.value} status")
            
            # If approved, need to restore inventory
            if transaction.status == TransactionStatus.APPROVED:
                item = InventoryItem.query.get(transaction.item_id)
                if item:
                    item.update_availability(1)
            
            # Update transaction status
            transaction.transition_to(TransactionStatus.CANCELLED, user_id, reason)
            
            db.session.commit()
            
            current_app.logger.info(f"Transaction cancelled: {transaction.transaction_id}")
            return transaction
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error cancelling transaction: {e}")
            raise
    
    @staticmethod
    def request_renewal(transaction_id, user_id, days=7):
        """
        Request renewal for a borrowed item
        
        Args:
            transaction_id: ID of the transaction to renew
            user_id: ID of the requesting user
            days: Number of days to extend
            
        Returns:
            Transaction: Updated transaction object
        """
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                raise ValueError("Transaction not found")
            
            # Validate user is the borrower
            if transaction.user_id != user_id:
                raise ValueError("User can only renew their own transactions")
            
            # Check renewal eligibility
            can_renew, reason = transaction.can_renew()
            if not can_renew:
                raise ValueError(reason)
            
            # Process renewal
            transaction.request_renewal(days)
            
            db.session.commit()
            
            current_app.logger.info(f"Renewal requested: {transaction.transaction_id}")
            
            # Log renewal request
            from app.models.audit_log import AuditLog, AuditAction
            AuditLog.log_action(
                action=AuditAction.RENEWAL_REQUEST,
                description=f"Renewal requested for {transaction.transaction_id}",
                target_type='Transaction',
                target_id=transaction.id,
                target_identifier=transaction.transaction_id,
                metadata={
                    'transaction_id': transaction.transaction_id,
                    'renewal_count': transaction.renew_count,
                    'new_due_date': transaction.due_date.isoformat(),
                    'days_extended': days
                }
            )
            
            return transaction
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error requesting renewal: {e}")
            raise
    
    @staticmethod
    def mark_overdue():
        """
        Mark overdue transactions (scheduled task)
        
        Returns:
            int: Number of transactions marked as overdue
        """
        try:
            # Find borrowed transactions past due date
            overdue_transactions = Transaction.query.filter(
                Transaction.status == TransactionStatus.BORROWED,
                Transaction.due_date < datetime.utcnow()
            ).all()
            
            count = 0
            for transaction in overdue_transactions:
                transaction.status = TransactionStatus.OVERDUE
                transaction.updated_at = datetime.utcnow()
                count += 1
                
                # Calculate accumulated fine
                fine_config = current_app.config.get('FINE_DAILY_RATE', Decimal('1.00'))
                transaction.calculate_fine(fine_config)
            
            db.session.commit()
            
            if count > 0:
                current_app.logger.info(f"Marked {count} transactions as overdue")
            
            return count
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error marking overdue transactions: {e}")
            raise
    
    @staticmethod
    def get_dashboard_stats(user_id=None, department_id=None):
        """
        Get transaction statistics for dashboard
        
        Args:
            user_id: Filter by specific user (optional)
            department_id: Filter by department (optional)
            
        Returns:
            dict: Dashboard statistics
        """
        try:
            base_query = Transaction.query
            
            if user_id:
                base_query = base_query.filter_by(user_id=user_id)
            elif department_id:
                from app.models.user import User
                base_query = base_query.join(User, Transaction.user_id == User.id).filter(User.department_id == department_id)
            
            # Current status counts
            pending_requests = base_query.filter_by(status=TransactionStatus.REQUESTED).count()
            approved_requests = base_query.filter_by(status=TransactionStatus.APPROVED).count()
            borrowed_items = base_query.filter_by(status=TransactionStatus.BORROWED).count()
            overdue_items = base_query.filter_by(status=TransactionStatus.OVERDUE).count()
            
            # Due soon (next 3 days)
            due_soon_threshold = datetime.utcnow() + timedelta(days=3)
            due_soon = base_query.filter(
                Transaction.status == TransactionStatus.BORROWED,
                Transaction.due_date <= due_soon_threshold,
                Transaction.due_date > datetime.utcnow()
            ).count()
            
            # Recent activity (last 7 days)
            recent_threshold = datetime.utcnow() - timedelta(days=7)
            recent_requests = base_query.filter(
                Transaction.requested_at >= recent_threshold
            ).count()
            
            return {
                'pending_requests': pending_requests,
                'approved_requests': approved_requests,
                'borrowed_items': borrowed_items,
                'overdue_items': overdue_items,
                'due_soon': due_soon,
                'recent_requests': recent_requests,
                'total_active': pending_requests + approved_requests + borrowed_items + overdue_items
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting dashboard stats: {e}")
            return {}


# Create service instance
transaction_service = TransactionService()