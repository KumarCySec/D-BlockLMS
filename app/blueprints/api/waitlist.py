"""
Waitlist API endpoints for queue management
"""
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from marshmallow import Schema, fields, ValidationError
from app.blueprints.api import bp
from app.models.waitlist import WaitlistRequest, WaitlistStatus
from app.models.inventory_item import InventoryItem
from app.utils.auth import role_required
from app import db


# Validation schemas
class WaitlistJoinSchema(Schema):
    """Schema for joining waitlist"""
    item_id = fields.Integer(required=True)
    notes = fields.String(allow_none=True, load_default=None)


class WaitlistSearchSchema(Schema):
    """Schema for waitlist search parameters"""
    status = fields.String(load_default=None)
    page = fields.Integer(load_default=1)
    per_page = fields.Integer(load_default=20)


@bp.route('/waitlist/join', methods=['POST'])
@login_required
def join_waitlist():
    """Join waitlist for an unavailable item"""
    try:
        # Validate request data
        schema = WaitlistJoinSchema()
        data = schema.load(request.get_json() or {})
        
        # Verify item exists
        item = InventoryItem.query.get(data['item_id'])
        if not item:
            return jsonify({
                'success': False,
                'message': 'Item not found'
            }), 404
        
        # Check if item is available
        if item.is_available():
            return jsonify({
                'success': False,
                'message': 'Item is currently available. You can request it directly.'
            }), 400
        
        # Join waitlist
        waitlist_request = WaitlistRequest.join_waitlist(
            user_id=current_user.id,
            item_id=data['item_id'],
            notes=data.get('notes')
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully joined waitlist at position {waitlist_request.position}',
            'data': {
                'waitlist_request': waitlist_request.to_dict(include_item=True),
                'estimated_wait_days': waitlist_request.get_estimated_wait_time()
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
        current_app.logger.error(f"Error joining waitlist: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/waitlist/<int:waitlist_id>/leave', methods=['DELETE'])
@login_required
def leave_waitlist(waitlist_id):
    """Leave waitlist"""
    try:
        # Get waitlist request
        waitlist_request = WaitlistRequest.query.get(waitlist_id)
        if not waitlist_request:
            return jsonify({
                'success': False,
                'message': 'Waitlist request not found'
            }), 404
        
        # Check ownership
        if waitlist_request.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'Waitlist request not found or access denied'
            }), 403
        
        # Cancel request
        waitlist_request.cancel_request("User cancelled")
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Successfully left waitlist',
            'data': {
                'waitlist_request': waitlist_request.to_dict(include_item=True)
            }
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error leaving waitlist: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/waitlist/<int:waitlist_id>/claim', methods=['POST'])
@login_required
def claim_waitlist_item(waitlist_id):
    """Claim item from waitlist notification"""
    try:
        # Get waitlist request
        waitlist_request = WaitlistRequest.query.get(waitlist_id)
        if not waitlist_request:
            return jsonify({
                'success': False,
                'message': 'Waitlist request not found'
            }), 404
        
        # Check ownership
        if waitlist_request.user_id != current_user.id:
            return jsonify({
                'success': False,
                'message': 'Waitlist request not found or access denied'
            }), 403
        
        # Claim item
        waitlist_request.claim_item()
        db.session.commit()
        
        # Create checkout request automatically
        from app.models.transaction import Transaction
        transaction = Transaction.create_request(
            user_id=current_user.id,
            item_id=waitlist_request.item_id,
            notes=f"Auto-created from waitlist claim #{waitlist_request.id}"
        )
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item claimed successfully. Checkout request created.',
            'data': {
                'waitlist_request': waitlist_request.to_dict(include_item=True),
                'transaction': transaction.to_dict(include_item=True)
            }
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error claiming waitlist item: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/waitlist/my', methods=['GET'])
@login_required
def get_my_waitlist():
    """Get current user's waitlist requests"""
    try:
        # Validate query parameters
        schema = WaitlistSearchSchema()
        params = schema.load(request.args.to_dict())
        
        # Get user's waitlist requests
        status_filter = None
        if params.get('status'):
            try:
                status_filter = [WaitlistStatus(params['status'])]
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': f"Invalid status: {params['status']}"
                }), 400
        
        waitlist_requests = WaitlistRequest.get_user_waitlist(
            user_id=current_user.id,
            status=status_filter
        )
        
        # Convert to dict
        requests = [
            req.to_dict(include_item=True)
            for req in waitlist_requests
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'waitlist_requests': requests,
                'count': len(requests)
            }
        })
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error getting user waitlist: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/items/<int:item_id>/waitlist', methods=['GET'])
@login_required
def get_item_waitlist(item_id):
    """Get waitlist for a specific item"""
    try:
        # Verify item exists
        item = InventoryItem.query.get(item_id)
        if not item:
            return jsonify({
                'success': False,
                'message': 'Item not found'
            }), 404
        
        # Get waitlist
        waitlist_requests = WaitlistRequest.get_item_waitlist(
            item_id=item_id,
            status=[WaitlistStatus.ACTIVE, WaitlistStatus.NOTIFIED]
        )
        
        # Convert to dict (include user info for admin/volunteers)
        include_user = current_user.has_role('Admin') or current_user.has_role('Incharge') or current_user.has_role('Volunteer')
        
        requests = [
            req.to_dict(include_user=include_user)
            for req in waitlist_requests
        ]
        
        # Get statistics
        stats = WaitlistRequest.get_waitlist_statistics(item_id)
        
        return jsonify({
            'success': True,
            'data': {
                'item': item.to_dict(),
                'waitlist_requests': requests,
                'statistics': stats
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting item waitlist: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/waitlist/notify/<int:waitlist_id>', methods=['POST'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def notify_waitlist_user(waitlist_id):
    """Manually notify waitlist user (admin/volunteer action)"""
    try:
        # Get waitlist request
        waitlist_request = WaitlistRequest.query.get(waitlist_id)
        if not waitlist_request:
            return jsonify({
                'success': False,
                'message': 'Waitlist request not found'
            }), 404
        
        # Check department permissions for non-admin users
        if not current_user.has_role('Admin'):
            if (current_user.department_id and 
                waitlist_request.user.department_id != current_user.department_id):
                return jsonify({
                    'success': False,
                    'message': 'Access denied'
                }), 403
        
        # Get claim hours from request (default 24)
        data = request.get_json() or {}
        claim_hours = data.get('claim_hours', 24)
        
        if not isinstance(claim_hours, int) or claim_hours < 1 or claim_hours > 168:  # Max 1 week
            return jsonify({
                'success': False,
                'message': 'Invalid claim hours (must be 1-168)'
            }), 400
        
        # Notify user
        waitlist_request.notify_availability(claim_hours)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'User notified. They have {claim_hours} hours to claim the item.',
            'data': {
                'waitlist_request': waitlist_request.to_dict(include_user=True, include_item=True)
            }
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error notifying waitlist user: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/waitlist/expired', methods=['GET'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def get_expired_claims():
    """Get expired waitlist claims that need processing"""
    try:
        # Get expired claims
        expired_claims = WaitlistRequest.get_expired_claims()
        
        # Filter by department for non-admin users
        if not current_user.has_role('Admin') and current_user.department_id:
            expired_claims = [
                claim for claim in expired_claims
                if claim.user.department_id == current_user.department_id
            ]
        
        # Convert to dict
        claims = [
            claim.to_dict(include_user=True, include_item=True)
            for claim in expired_claims
        ]
        
        return jsonify({
            'success': True,
            'data': {
                'expired_claims': claims,
                'count': len(claims)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting expired claims: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/waitlist/cleanup', methods=['POST'])
@login_required
@role_required('Admin', 'Incharge')
def cleanup_expired_claims():
    """Process expired claims and notify next in queue"""
    try:
        # Cleanup expired claims
        expired_count, processed_items = WaitlistRequest.cleanup_expired_claims()
        
        return jsonify({
            'success': True,
            'message': f'Processed {expired_count} expired claims for {processed_items} items',
            'data': {
                'expired_claims_processed': expired_count,
                'items_processed': processed_items
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error cleaning up expired claims: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/waitlist/statistics', methods=['GET'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def get_waitlist_statistics():
    """Get overall waitlist statistics"""
    try:
        # Get overall statistics
        stats = WaitlistRequest.get_waitlist_statistics()
        
        return jsonify({
            'success': True,
            'data': {
                'statistics': stats
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting waitlist statistics: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500