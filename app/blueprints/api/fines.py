"""
Fine management API endpoints
"""
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from marshmallow import Schema, fields, ValidationError
from app.blueprints.api import bp
from app.models.fine import FineRecord, FineConfiguration, FineService
from app.models.user import User
from app.utils.auth import role_required
from app import db
from decimal import Decimal
from datetime import datetime, date


# Validation schemas
class FineConfigurationSchema(Schema):
    """Schema for fine configuration"""
    item_type = fields.String(required=True)
    daily_rate = fields.Decimal(required=True, places=2)
    grace_period_days = fields.Integer(load_default=0)
    max_fine_amount = fields.Decimal(allow_none=True, places=2, load_default=None)
    escalation_days = fields.Integer(load_default=7)


class FineWaiverSchema(Schema):
    """Schema for fine waiver"""
    reason = fields.String(required=True)


class FineReportSchema(Schema):
    """Schema for fine report parameters"""
    start_date = fields.Date(load_default=None)
    end_date = fields.Date(load_default=None)
    department_id = fields.Integer(load_default=None)
    user_id = fields.Integer(load_default=None)
    include_waived = fields.Boolean(load_default=False)
    page = fields.Integer(load_default=1)
    per_page = fields.Integer(load_default=50)


@bp.route('/fines/config', methods=['GET'])
@login_required
@role_required('Admin', 'Incharge')
def get_fine_configurations():
    """Get all fine configurations"""
    try:
        configurations = FineConfiguration.get_all_active()
        
        configs = [config.to_dict() for config in configurations]
        
        return jsonify({
            'success': True,
            'data': {
                'configurations': configs
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting fine configurations: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/fines/config', methods=['POST'])
@login_required
@role_required('Admin')
def update_fine_configuration():
    """Update fine configuration (Admin only)"""
    try:
        # Validate request data
        schema = FineConfigurationSchema()
        data = schema.load(request.get_json() or {})
        
        # Validate item type
        valid_types = ['book', 'laptop', 'kit']
        if data['item_type'] not in valid_types:
            return jsonify({
                'success': False,
                'message': f"Invalid item type. Must be one of: {', '.join(valid_types)}"
            }), 400
        
        # Update configuration
        config = FineConfiguration.update_configuration(
            item_type=data['item_type'],
            daily_rate=data['daily_rate'],
            grace_period_days=data.get('grace_period_days', 0),
            max_fine_amount=data.get('max_fine_amount'),
            escalation_days=data.get('escalation_days', 7),
            updated_by=current_user.id
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Fine configuration updated for {data["item_type"]}',
            'data': {
                'configuration': config.to_dict()
            }
        })
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error updating fine configuration: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/fines/user/<int:user_id>', methods=['GET'])
@login_required
def get_user_fines(user_id):
    """Get fine summary for a specific user"""
    try:
        # Check permissions
        if current_user.has_role('Student'):
            if user_id != current_user.id:
                return jsonify({
                    'success': False,
                    'message': 'Access denied'
                }), 403
        elif current_user.has_role('Volunteer') or current_user.has_role('Incharge'):
            # Check if user is in same department
            user = User.query.get(user_id)
            if not user or (current_user.department_id and 
                          user.department_id != current_user.department_id):
                return jsonify({
                    'success': False,
                    'message': 'User not found or access denied'
                }), 403
        
        # Get user fine summary
        summary = FineService.get_user_fine_summary(user_id)
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user fines: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/fines/my', methods=['GET'])
@login_required
def get_my_fines():
    """Get current user's fine summary"""
    try:
        summary = FineService.get_user_fine_summary(current_user.id)
        
        return jsonify({
            'success': True,
            'data': summary
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting user fines: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/fines/<int:fine_id>/waive', methods=['POST'])
@login_required
@role_required('Admin', 'Incharge')
def waive_fine(fine_id):
    """Waive a fine record"""
    try:
        # Validate request data
        schema = FineWaiverSchema()
        data = schema.load(request.get_json() or {})
        
        # Get fine record
        fine_record = FineRecord.query.get(fine_id)
        if not fine_record:
            return jsonify({
                'success': False,
                'message': 'Fine record not found'
            }), 404
        
        # Check department permissions for Incharge
        if current_user.has_role('Incharge') and not current_user.has_role('Admin'):
            if (current_user.department_id and 
                fine_record.user.department_id != current_user.department_id):
                return jsonify({
                    'success': False,
                    'message': 'Access denied'
                }), 403
        
        # Waive fine
        fine_record.waive_fine(
            waiver_user_id=current_user.id,
            reason=data['reason']
        )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Fine of ₹{fine_record.fine_amount} waived successfully',
            'data': {
                'fine_record': fine_record.to_dict(include_user=True, include_item=True, include_transaction=True)
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
        current_app.logger.error(f"Error waiving fine: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/fines/reports/student', methods=['GET'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def get_student_fine_reports():
    """Get per-student fine reports"""
    try:
        # Validate query parameters
        schema = FineReportSchema()
        params = schema.load(request.args.to_dict())
        
        # Get department filter for non-admin users
        department_id = params.get('department_id')
        if not current_user.has_role('Admin') and current_user.department_id:
            department_id = current_user.department_id
        
        # Get fine statistics
        stats = FineRecord.get_fine_statistics(
            start_date=params.get('start_date'),
            end_date=params.get('end_date'),
            department_id=department_id
        )
        
        # Get pending fines by user
        pending_fines = FineRecord.get_pending_fines(department_id)
        
        # Group by user
        user_fines = {}
        for fine in pending_fines:
            user_id = fine.user_id
            if user_id not in user_fines:
                user_fines[user_id] = {
                    'user': fine.user.to_dict(),
                    'fines': [],
                    'total_amount': 0.0,
                    'fine_count': 0
                }
            
            user_fines[user_id]['fines'].append(
                fine.to_dict(include_item=True, include_transaction=True)
            )
            user_fines[user_id]['total_amount'] += float(fine.fine_amount)
            user_fines[user_id]['fine_count'] += 1
        
        # Convert to list and sort by total amount
        student_reports = list(user_fines.values())
        student_reports.sort(key=lambda x: x['total_amount'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'statistics': stats,
                'student_reports': student_reports,
                'total_students_with_fines': len(student_reports)
            }
        })
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error getting student fine reports: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/fines/reports/department', methods=['GET'])
@login_required
@role_required('Admin', 'Incharge')
def get_department_fine_reports():
    """Get department-wise fine summaries"""
    try:
        from app.models.department import Department
        
        # Get all departments (or just user's department for Incharge)
        if current_user.has_role('Admin'):
            departments = Department.get_active_departments()
        else:
            departments = [current_user.department] if current_user.department else []
        
        department_reports = []
        
        for department in departments:
            summary = FineService.get_department_fine_summary(department.id)
            summary['department'] = department.to_dict()
            department_reports.append(summary)
        
        # Sort by pending amount
        department_reports.sort(key=lambda x: x['pending_amount'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'department_reports': department_reports,
                'total_departments': len(department_reports)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting department fine reports: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/fines/calculate', methods=['POST'])
@login_required
@role_required('Admin')
def calculate_daily_fines():
    """Manually trigger daily fine calculation (Admin only)"""
    try:
        # Create daily fine records
        created_records = FineService.create_daily_fine_records()
        
        total_amount = sum(float(record.fine_amount) for record in created_records)
        
        return jsonify({
            'success': True,
            'message': f'Created {len(created_records)} fine records totaling ₹{total_amount:.2f}',
            'data': {
                'records_created': len(created_records),
                'total_amount': total_amount,
                'fine_records': [
                    record.to_dict(include_user=True, include_item=True, include_transaction=True)
                    for record in created_records
                ]
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error calculating daily fines: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/fines/statistics', methods=['GET'])
@login_required
@role_required('Admin', 'Incharge', 'Volunteer')
def get_fine_statistics():
    """Get fine statistics"""
    try:
        # Validate query parameters
        schema = FineReportSchema()
        params = schema.load(request.args.to_dict())
        
        # Get department filter for non-admin users
        department_id = params.get('department_id')
        if not current_user.has_role('Admin') and current_user.department_id:
            department_id = current_user.department_id
        
        # Get statistics
        stats = FineRecord.get_fine_statistics(
            start_date=params.get('start_date'),
            end_date=params.get('end_date'),
            department_id=department_id
        )
        
        return jsonify({
            'success': True,
            'data': {
                'statistics': stats
            }
        })
        
    except ValidationError as e:
        return jsonify({
            'success': False,
            'message': 'Validation failed',
            'errors': e.messages
        }), 400
        
    except Exception as e:
        current_app.logger.error(f"Error getting fine statistics: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@bp.route('/transactions/<int:transaction_id>/fine', methods=['GET'])
@login_required
def get_transaction_fine(transaction_id):
    """Get fine information for a transaction"""
    try:
        from app.models.transaction import Transaction
        
        # Get transaction
        transaction = Transaction.query.get(transaction_id)
        if not transaction:
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
        
        # Check permissions
        if current_user.has_role('Student'):
            if transaction.user_id != current_user.id:
                return jsonify({
                    'success': False,
                    'message': 'Access denied'
                }), 403
        elif current_user.has_role('Volunteer') or current_user.has_role('Incharge'):
            if (current_user.department_id and 
                transaction.user.department_id != current_user.department_id):
                return jsonify({
                    'success': False,
                    'message': 'Access denied'
                }), 403
        
        # Calculate current fine
        current_fine = FineService.calculate_transaction_fine(transaction)
        
        # Get fine records for this transaction
        fine_records = FineRecord.get_transaction_fines(transaction_id)
        
        # Calculate totals
        total_fines = sum(float(record.fine_amount) for record in fine_records)
        pending_fines = sum(float(record.fine_amount) for record in fine_records if not record.is_waived)
        waived_fines = sum(float(record.fine_amount) for record in fine_records if record.is_waived)
        
        return jsonify({
            'success': True,
            'data': {
                'transaction': transaction.to_dict(include_item=True),
                'current_fine': str(current_fine),
                'fine_summary': {
                    'total_fines': total_fines,
                    'pending_fines': pending_fines,
                    'waived_fines': waived_fines,
                    'record_count': len(fine_records)
                },
                'fine_records': [
                    record.to_dict()
                    for record in fine_records
                ]
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting transaction fine: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500