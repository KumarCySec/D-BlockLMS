"""
Transaction API endpoints for checkout/return workflow
"""
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from marshmallow import Schema, fields, ValidationError
from app.blueprints.api import bp
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.models.inventory_item import InventoryItem
from app.utils.transaction_service import transaction_service
from app.utils.auth import role_required
from app import db


# Validation schemas
class TransactionRequestSchema(Schema):
    """Schema for transaction request validation"""
    item_id = fields.Integer(required=True)
    notes = fields.String(allow_none=True, load_default=None)


class TransactionApprovalSchema(Schema):
    """Schema for transaction approval validation"""
    notes = fields.String(allow_none=True, load_default=None)


class TransactionSearchSchema(Schema):
    """Schema for transaction search parameters"""
    status = fields.String(load_default=None)
    user_id = fields.Integer(load_default=None)
    item_id = fields.Integer(load_default=None)
    start_date = fields.DateTime(load_default=None)
    end_date = fields.DateTime(load_default=None)
    page = fields.Integer(load_default=1)
    per_page = fields.Integer(load_default=20)


@bp.route('/transactions/request', methods=['POST'])
@login_required
def create_transaction_request():
    """Create a new checkout request"""
    try:
        # Validate request data
        schema = TransactionRequestSchema()
        data = schema.load(request.get_json() or {})
        
        # Create checkout request
        transaction = transaction_service.create_checkout_request(
            user_id=current_user.id,
            item_id=data['item_id'],
            notes=data.get('notes')
        )
        
        return jsonify({
            'success': True,
            'message': 'Checkout request created successfully',
            'data': {
                'transaction': transaction.to_dict(include_item=True)
            }
        }), 201
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error creating transaction request: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/<int:transaction_id>/approve', methods=['POST', 'PUT'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def approve_transaction(transaction_id):
    """Approve a checkout request"""
    try:
        # Validate request data
        schema = TransactionApprovalSchema()
        data = schema.load(request.get_json() or {})
        
        # Approve transaction
        transaction = transaction_service.approve_request(
            transaction_id=transaction_id,
            approver_id=current_user.id,
            notes=data.get('notes')
        )
        
        return jsonify({
            'success': True,
            'message': 'Transaction approved successfully',
            'data': {
                'transaction': transaction.to_dict(include_user=True, include_item=True, include_approver=True)
            }
        })
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error approving transaction: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/<int:transaction_id>/reject', methods=['POST', 'PUT'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def reject_transaction(transaction_id):
    """Reject a checkout request"""
    try:
        # Validate request data
        schema = TransactionApprovalSchema()
        data = schema.load(request.get_json() or {})
        
        # Reject transaction
        transaction = transaction_service.reject_request(
            transaction_id=transaction_id,
            approver_id=current_user.id,
            reason=data.get('notes')
        )
        
        return jsonify({
            'success': True,
            'message': 'Transaction rejected successfully',
            'data': {
                'transaction': transaction.to_dict(include_user=True, include_item=True, include_approver=True)
            }
        })
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error rejecting transaction: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/<int:transaction_id>/issue', methods=['POST', 'PUT'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def issue_item(transaction_id):
    """Mark approved item as issued (borrowed)"""
    try:
        # Issue item
        transaction = transaction_service.issue_item(
            transaction_id=transaction_id,
            issuer_id=current_user.id
        )
        
        return jsonify({
            'success': True,
            'message': 'Item issued successfully',
            'data': {
                'transaction': transaction.to_dict(include_user=True, include_item=True)
            }
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error issuing item: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/<int:transaction_id>/return', methods=['POST', 'PUT'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def process_return(transaction_id):
    """Process item return"""
    try:
        # Validate request data
        schema = TransactionApprovalSchema()
        data = schema.load(request.get_json() or {})
        
        # Process return
        transaction = transaction_service.process_return(
            transaction_id=transaction_id,
            processor_id=current_user.id,
            notes=data.get('notes')
        )
        
        return jsonify({
            'success': True,
            'message': 'Item returned successfully',
            'data': {
                'transaction': transaction.to_dict(include_user=True, include_item=True),
                'fine_amount': str(transaction.fine_accumulated) if transaction.fine_accumulated > 0 else None
            }
        })
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error processing return: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/<int:transaction_id>/cancel', methods=['PUT'])
@login_required
def cancel_transaction(transaction_id):
    """Cancel a pending transaction"""
    try:
        # Validate request data
        schema = TransactionApprovalSchema()
        data = schema.load(request.get_json() or {})
        
        # Cancel transaction
        transaction = transaction_service.cancel_request(
            transaction_id=transaction_id,
            user_id=current_user.id,
            reason=data.get('notes')
        )
        
        return jsonify({
            'success': True,
            'message': 'Transaction cancelled successfully',
            'data': {
                'transaction': transaction.to_dict(include_item=True)
            }
        })
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error cancelling transaction: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/<int:transaction_id>/renew', methods=['POST', 'PUT'])
@login_required
def request_renewal(transaction_id):
    """Request renewal for borrowed item"""
    try:
        # Get renewal days from request (default 7)
        data = request.get_json() or {}
        days = data.get('days', 7)
        
        if not isinstance(days, int) or days < 1 or days > 30:
            return jsonify({
                'success': False,
                'message': 'Invalid renewal days (must be 1-30)'
            }), 400
        
        # Get transaction first to check permissions
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({
                'success': False,
                'message': 'Transaction not found or access denied'
            }), 400
        
        # Check if user owns the transaction
        if transaction.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'Transaction not found or access denied'
            }), 400
        
        # Check if item has waitlist
        from app.models.waitlist import WaitlistRequest, WaitlistStatus
        active_waitlist = WaitlistRequest.query.filter_by(
            item_id=transaction.item_id,
            status=WaitlistStatus.ACTIVE
        ).first()
        
        if active_waitlist:
            return jsonify({
                'success': False,
                'message': 'Renewal blocked: Item has active waitlist. Please contact library staff for approval.',
                'requires_approval': True,
                'waitlist_count': len(WaitlistRequest.get_item_waitlist(transaction.item_id, [WaitlistStatus.ACTIVE]))
            }), 400
        
        # Request renewal
        transaction = transaction_service.request_renewal(
            transaction_id=transaction_id,
            user_id=current_user.id,
            days=days
        )
        
        return jsonify({
            'success': True,
            'message': f'Renewal requested for {days} days',
            'data': {
                'transaction': transaction.to_dict(include_item=True)
            },
            'new_due_date': transaction.due_date.isoformat(),
            'renewals_remaining': transaction.max_renewals - transaction.renew_count
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error requesting renewal: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/<int:transaction_id>/renew/approve', methods=['POST'])
@login_required
@role_required('Admin', 'Incharge')
def approve_renewal_override(transaction_id):
    """Approve renewal override when item has waitlist (Incharge/Admin only)"""
    try:
        # Get renewal days from request (default 7)
        data = request.get_json() or {}
        days = data.get('days', 7)
        reason = data.get('reason', 'Renewal approved by staff')
        
        if not isinstance(days, int) or days < 1 or days > 30:
            return jsonify({
                'success': False,
                'message': 'Invalid renewal days (must be 1-30)'
            }), 400
        
        # Get transaction
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
        
        # Check department permissions for Incharge
        if current_user.has_role('Incharge') and not current_user.has_role('Admin'):
            if (current_user.department_id and 
                transaction.user.department_id != current_user.department_id):
                return jsonify({
                    'success': False,
                    'message': 'Access denied'
                }), 403
        
        # Force renewal (bypass waitlist check)
        can_renew, message = transaction.can_renew()
        if not can_renew and "Maximum renewals" not in message:
            # Only allow override for waitlist conflicts, not renewal limits
            pass
        elif not can_renew:
            return jsonify({
                'success': False,
                'message': message
            }), 400
        
        # Approve renewal
        transaction.request_renewal(days)
        
        # Log the override
        from app.models.audit_log import AuditLog, AuditAction
        AuditLog.log_action(
            action=AuditAction.RENEWAL_APPROVE,
            description=f"Renewal override approved for transaction {transaction.transaction_id}",
            target_type='Transaction',
            target_id=transaction.id,
            target_identifier=transaction.transaction_id,
            metadata={
                'transaction_id': transaction.transaction_id,
                'days': days,
                'reason': reason,
                'approver_id': current_user.id,
                'user_id': transaction.user_id
            }
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Renewal approved for {days} days (override)',
            'data': {
                'transaction': transaction.to_dict(include_item=True)
            },
            'new_due_date': transaction.due_date.isoformat(),
            'renewals_remaining': transaction.max_renewals - transaction.renew_count,
            'approved_by': current_user.name
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error approving renewal override: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions', methods=['GET'])
@login_required
def list_transactions():
    """List transactions with filtering and pagination"""
    try:
        # Validate query parameters
        schema = TransactionSearchSchema()
        params = schema.load(request.args.to_dict())
        
        # Build query based on user role
        query = Transaction.query
        
        # Role-based filtering
        if current_user.has_role('Student'):
            # Students can only see their own transactions
            query = query.filter_by(user_id=current_user.id)
        elif current_user.has_role('Volunteer'):
            # Volunteers can see transactions for their department
            if current_user.department_id:
                query = query.join(Transaction.user).filter_by(department_id=current_user.department_id)
        elif current_user.has_role('Incharge'):
            # Incharge can see transactions for their department
            if current_user.department_id:
                query = query.join(Transaction.user).filter_by(department_id=current_user.department_id)
        # Admin can see all transactions (no additional filter)
        
        # Apply filters
        if params.get('status'):
            try:
                status = TransactionStatus(params['status'])
                query = query.filter_by(status=status)
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f"Invalid status: {params['status']}"
                }), 400
        
        if params.get('user_id') and current_user.has_role('Admin'):
            query = query.filter_by(user_id=params['user_id'])
        
        if params.get('item_id'):
            query = query.filter_by(item_id=params['item_id'])
        
        if params.get('start_date'):
            query = query.filter(Transaction.requested_at >= params['start_date'])
        
        if params.get('end_date'):
            query = query.filter(Transaction.requested_at <= params['end_date'])
        
        # Order by most recent first
        query = query.order_by(Transaction.requested_at.desc())
        
        # Pagination
        page = params.get('page', 1)
        per_page = min(params.get('per_page', 20), 100)  # Max 100 per page
        
        paginated = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        # Convert to dict
        transactions = [
            t.to_dict(include_user=True, include_item=True, include_approver=True)
            for t in paginated.items
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'transactions': transactions,
                'pagination': {
                    'page': paginated.page,
                    'per_page': paginated.per_page,
                    'total': paginated.total,
                    'pages': paginated.pages,
                    'has_next': paginated.has_next,
                    'has_prev': paginated.has_prev
                }
            }
        })
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error listing transactions: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/<int:transaction_id>', methods=['GET'])
@login_required
def get_transaction(transaction_id):
    """Get transaction details"""
    try:
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({
                'success': False,
                'message': 'Transaction not found or access denied'
            }), 404
        
        # Check permissions
        if current_user.has_role('Student'):
            if transaction.user_id != current_user.id:
                return jsonify({
                    'success': False,
                    'message': 'Transaction not found or access denied'
                }), 403
        elif current_user.has_role('Volunteer') or current_user.has_role('Incharge'):
            if (current_user.department_id and 
                transaction.user.department_id != current_user.department_id):
                return jsonify({
                    'success': False,
                    'message': 'Transaction not found or access denied'
                }), 403
        
        return jsonify({
            'success': True,
            'data': {
                'transaction': transaction.to_dict(include_user=True, include_item=True, include_approver=True)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting transaction: {e}")
        return jsonify({
            'success': False,
            'message': 'Transaction not found or access denied'
        }), 400


@bp.route('/transactions/pending', methods=['GET'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def get_pending_approvals():
    """Get transactions pending approval"""
    try:
        # Get department filter for non-admin users
        department_id = None
        if not current_user.has_role('Admin') and current_user.department_id:
            department_id = current_user.department_id
        
        # Get pending transactions
        pending_transactions = Transaction.get_pending_approvals(department_id)
        
        # Convert to dict
        transactions = [
            t.to_dict(include_user=True, include_item=True)
            for t in pending_transactions
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'transactions': transactions,
                'count': len(transactions)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting pending approvals: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/dashboard', methods=['GET'])
@login_required
def get_transaction_dashboard():
    """Get transaction dashboard statistics"""
    try:
        # Get user/department filter
        user_id = None
        department_id = None
        
        if current_user.has_role('Student'):
            user_id = current_user.id
        elif not current_user.has_role('Admin') and current_user.department_id:
            department_id = current_user.department_id
        
        # Get dashboard stats
        stats = transaction_service.get_dashboard_stats(user_id, department_id)
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/overdue', methods=['GET'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def get_overdue_transactions():
    """Get overdue transactions"""
    try:
        # Get overdue transactions
        overdue_transactions = Transaction.get_overdue_transactions()
        
        # Filter by department for non-admin users
        if not current_user.has_role('Admin') and current_user.department_id:
            overdue_transactions = [
                t for t in overdue_transactions
                if t.user.department_id == current_user.department_id
            ]
        
        # Convert to dict
        transactions = [
            t.to_dict(include_user=True, include_item=True)
            for t in overdue_transactions
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'transactions': transactions,
                'count': len(transactions)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting overdue transactions: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/items/<int:item_id>/history', methods=['GET'])
@login_required
def get_item_history(item_id):
    """Get transaction history for an item"""
    try:
        # Verify item exists
        item = InventoryItem.query.get_or_404(item_id)
        
        # Get transaction history
        limit = request.args.get('limit', 50, type=int)
        limit = min(limit, 100)  # Max 100 records
        
        transactions = Transaction.get_item_history(item_id, limit)
        
        # Convert to dict
        history = [
            t.to_dict(include_user=True, include_approver=True)
            for t in transactions
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'item': item.to_dict(),
                'history': history,
                'count': len(history)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting item history: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500