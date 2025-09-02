"""
Inventory management API endpoints
"""
from datetime import datetime, date
from flask import request, current_app
from flask_login import current_user
from marshmallow import Schema, fields, ValidationError, validates_schema
from marshmallow.validate import OneOf, Length, Range
from app.blueprints.api import bp
from app.blueprints.api.routes import APIResponse
from app.utils.auth import login_required_with_status, role_required
from app.utils.search import SearchService
from app.models.inventory_item import InventoryItem, ItemType
from app.models.donor import Donor
from app.models.department import Department
from app.utils.audit import audit_action
from app.utils.cache import invalidate_inventory_cache, invalidate_donor_cache
from app import db


# Validation schemas with improved error messages
class DonorSchema(Schema):
    """Schema for donor validation with detailed error messages"""
    name = fields.Str(
        required=True, 
        validate=Length(min=1, max=100),
        error_messages={
            'required': 'Donor name is required',
            'invalid': 'Donor name must be a valid string',
            'validator_failed': 'Donor name must be between 1 and 100 characters'
        }
    )
    branch = fields.Str(
        required=True, 
        validate=Length(min=1, max=50),
        error_messages={
            'required': 'Branch is required',
            'invalid': 'Branch must be a valid string',
            'validator_failed': 'Branch must be between 1 and 50 characters'
        }
    )
    batch = fields.Str(
        required=True, 
        validate=Length(min=1, max=10),
        error_messages={
            'required': 'Batch is required',
            'invalid': 'Batch must be a valid string',
            'validator_failed': 'Batch must be between 1 and 10 characters'
        }
    )
    address = fields.Str(
        allow_none=True, 
        validate=Length(max=500),
        error_messages={
            'invalid': 'Address must be a valid string',
            'validator_failed': 'Address cannot exceed 500 characters'
        }
    )
    phone = fields.Str(
        allow_none=True, 
        validate=Length(max=15),
        error_messages={
            'invalid': 'Phone number must be a valid string',
            'validator_failed': 'Phone number cannot exceed 15 characters'
        }
    )
    email = fields.Email(
        allow_none=True,
        error_messages={
            'invalid': 'Invalid email format. Please enter a valid email address'
        }
    )
    notes = fields.Str(
        allow_none=True, 
        validate=Length(max=1000),
        error_messages={
            'invalid': 'Notes must be a valid string',
            'validator_failed': 'Notes cannot exceed 1000 characters'
        }
    )


class InventoryItemSchema(Schema):
    """Schema for inventory item validation with detailed error messages"""
    item_type = fields.Str(
        required=True, 
        validate=OneOf([t.value for t in ItemType]),
        error_messages={
            'required': 'Item type is required',
            'invalid': 'Item type must be a valid string',
            'validator_failed': f'Item type must be one of: {", ".join([t.value for t in ItemType])}'
        }
    )
    title = fields.Str(
        required=True, 
        validate=Length(min=1, max=200),
        error_messages={
            'required': 'Title is required',
            'invalid': 'Title must be a valid string',
            'validator_failed': 'Title must be between 1 and 200 characters'
        }
    )
    authors = fields.Str(
        allow_none=True, 
        validate=Length(max=200),
        error_messages={
            'invalid': 'Authors must be a valid string',
            'validator_failed': 'Authors cannot exceed 200 characters'
        }
    )
    language = fields.Str(
        allow_none=True, 
        validate=Length(max=50),
        error_messages={
            'invalid': 'Language must be a valid string',
            'validator_failed': 'Language cannot exceed 50 characters'
        }
    )
    published_date = fields.Date(
        allow_none=True,
        error_messages={
            'invalid': 'Published date must be in YYYY-MM-DD format'
        }
    )
    sku_code = fields.Str(
        allow_none=True, 
        validate=Length(max=50),
        error_messages={
            'invalid': 'SKU code must be a valid string',
            'validator_failed': 'SKU code cannot exceed 50 characters'
        }
    )
    description = fields.Str(
        allow_none=True, 
        validate=Length(max=1000),
        error_messages={
            'invalid': 'Description must be a valid string',
            'validator_failed': 'Description cannot exceed 1000 characters'
        }
    )
    donor_id = fields.Int(
        required=True,
        error_messages={
            'required': 'Donor ID is required',
            'invalid': 'Donor ID must be a valid integer'
        }
    )
    date_of_donation = fields.Date(
        required=True,
        error_messages={
            'required': 'Date of donation is required',
            'invalid': 'Date of donation must be in YYYY-MM-DD format'
        }
    )
    total_quantity = fields.Int(
        required=True, 
        validate=Range(min=1),
        error_messages={
            'required': 'Total quantity is required',
            'invalid': 'Total quantity must be a valid integer',
            'validator_failed': 'Total quantity must be at least 1'
        }
    )
    department_id = fields.Int(
        allow_none=True,
        error_messages={
            'invalid': 'Department ID must be a valid integer'
        }
    )
    
    @validates_schema
    def validate_donor_exists(self, data, **kwargs):
        """Validate that donor exists"""
        donor_id = data.get('donor_id')
        if donor_id:
            donor = Donor.query.get(donor_id)
            if not donor:
                raise ValidationError('The specified donor does not exist. Please select a valid donor.', 'donor_id')
    
    @validates_schema
    def validate_department_exists(self, data, **kwargs):
        """Validate that department exists if provided"""
        dept_id = data.get('department_id')
        if dept_id:
            department = Department.query.get(dept_id)
            if not department:
                raise ValidationError('The specified department does not exist. Please select a valid department.', 'department_id')


# Donor management endpoints
@bp.route('/donors', methods=['GET'])
@login_required_with_status
def get_donors():
    """Get donors list with search and filtering"""
    try:
        # Get query parameters
        query = request.args.get('q', '').strip()
        branch = request.args.get('branch')
        batch = request.args.get('batch')
        sort_by = request.args.get('sort', 'name')
        sort_order = request.args.get('order', 'asc')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Build filters
        filters = {}
        if branch:
            filters['branch'] = branch
        if batch:
            filters['batch'] = batch
        
        # Search donors
        donors, total_count = SearchService.search_donors(
            query=query,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )
        
        # Convert to dict
        donors_data = [donor.to_dict(include_stats=True) for donor in donors]
        
        # Get filter options
        branches = Donor.get_branches()
        batches = Donor.get_batches()
        
        return APIResponse.success({
            'donors': donors_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page,
                'has_next': page * per_page < total_count,
                'has_prev': page > 1
            },
            'filters': {
                'branches': branches,
                'batches': batches
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching donors: {e}")
        return APIResponse.error("Failed to fetch donors", 500)


@bp.route('/donors/<int:donor_id>', methods=['GET'])
@login_required_with_status
def get_donor(donor_id):
    """Get specific donor details with donation history"""
    try:
        donor = Donor.query.get_or_404(donor_id)
        
        # Get donor's donations
        donations = InventoryItem.query.filter_by(donor_id=donor_id).all()
        donations_data = [item.to_dict(include_donor=False) for item in donations]
        
        donor_data = donor.to_dict(include_stats=True)
        donor_data['donations'] = donations_data
        
        return APIResponse.success({'donor': donor_data})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching donor {donor_id}: {e}")
        return APIResponse.error("Failed to fetch donor", 500)


@bp.route('/donors', methods=['POST'])
@role_required('Admin', 'Incharge')
def create_donor():
    """Create new donor"""
    try:
        # Validate input
        schema = DonorSchema()
        data = schema.load(request.get_json())
        
        # Check for duplicate email if provided
        if data.get('email'):
            existing_donor = Donor.get_by_email(data['email'])
            if existing_donor:
                return APIResponse.error("Donor with this email already exists", 400)
        
        # Create donor
        donor = Donor(**data)
        db.session.add(donor)
        db.session.commit()
        
        # Invalidate cache
        invalidate_donor_cache()
        
        # Audit log
        audit_action(
            actor_id=current_user.id,
            action='DONOR_CREATED',
            target_type='donor',
            target_id=donor.id,
            details={'donor_name': donor.name, 'branch': donor.branch, 'batch': donor.batch}
        )
        
        return APIResponse.success(
            {'donor': donor.to_dict()},
            f"Donor {donor.name} created successfully",
            201
        )
        
    except ValidationError as e:
        return APIResponse.validation_error(e.messages)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating donor: {e}")
        return APIResponse.error("Failed to create donor", 500)


@bp.route('/donors/<int:donor_id>', methods=['PUT'])
@role_required('Admin', 'Incharge')
def update_donor(donor_id):
    """Update donor information"""
    try:
        donor = Donor.query.get_or_404(donor_id)
        
        # Validate input
        schema = DonorSchema()
        data = schema.load(request.get_json())
        
        # Check for duplicate email if changed
        if data.get('email') and data['email'] != donor.email:
            existing_donor = Donor.get_by_email(data['email'])
            if existing_donor:
                return APIResponse.error("Donor with this email already exists", 400)
        
        # Store old values for audit
        old_values = donor.to_dict()
        
        # Update donor
        for key, value in data.items():
            setattr(donor, key, value)
        
        donor.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Audit log
        audit_action(
            actor_id=current_user.id,
            action='DONOR_UPDATED',
            target_type='donor',
            target_id=donor.id,
            details={'old_values': old_values, 'new_values': donor.to_dict()}
        )
        
        return APIResponse.success(
            {'donor': donor.to_dict()},
            f"Donor {donor.name} updated successfully"
        )
        
    except ValidationError as e:
        return APIResponse.validation_error(e.messages)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating donor {donor_id}: {e}")
        return APIResponse.error("Failed to update donor", 500)


@bp.route('/donors/<int:donor_id>', methods=['DELETE'])
@role_required('Admin')
def delete_donor(donor_id):
    """Delete donor (Admin only)"""
    try:
        donor = Donor.query.get_or_404(donor_id)
        
        # Check if donor has associated inventory items
        if donor.get_donation_count() > 0:
            return APIResponse.error(
                "Cannot delete donor with associated inventory items", 400
            )
        
        donor_name = donor.name
        db.session.delete(donor)
        db.session.commit()
        
        # Audit log
        audit_action(
            actor_id=current_user.id,
            action='DONOR_DELETED',
            target_type='donor',
            target_id=donor_id,
            details={'donor_name': donor_name}
        )
        
        return APIResponse.success(
            message=f"Donor {donor_name} deleted successfully"
        )
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting donor {donor_id}: {e}")
        return APIResponse.error("Failed to delete donor", 500)


# Inventory management endpoints
@bp.route('/inventory', methods=['GET'])
@login_required_with_status
def get_inventory():
    """Get inventory items with advanced search and filtering"""
    try:
        # Get query parameters
        query = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        sort_by = request.args.get('sort', 'title')
        sort_order = request.args.get('order', 'asc')
        
        # Build filters from query parameters
        filters = {}
        
        # Multi-value filters (can be comma-separated)
        if request.args.get('type'):
            types = request.args.get('type').split(',')
            filters['item_type'] = types if len(types) > 1 else types[0]
        
        if request.args.get('language'):
            languages = request.args.get('language').split(',')
            filters['language'] = languages if len(languages) > 1 else languages[0]
        
        if request.args.get('department'):
            departments = [int(d) for d in request.args.get('department').split(',')]
            filters['department'] = departments if len(departments) > 1 else departments[0]
        
        if request.args.get('donor'):
            donors = [int(d) for d in request.args.get('donor').split(',')]
            filters['donor'] = donors if len(donors) > 1 else donors[0]
        
        # Single value filters
        if request.args.get('availability'):
            filters['availability'] = request.args.get('availability')
        
        if request.args.get('donor_batch'):
            filters['donor_batch'] = request.args.get('donor_batch')
        
        if request.args.get('donor_branch'):
            filters['donor_branch'] = request.args.get('donor_branch')
        
        # Search inventory
        items, total_count, filter_options = SearchService.search_inventory(
            query=query,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            per_page=per_page
        )
        
        # Convert to dict
        items_data = [item.to_dict(include_donor=True, include_stats=True) for item in items]
        
        return APIResponse.success({
            'items': items_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': (total_count + per_page - 1) // per_page,
                'has_next': page * per_page < total_count,
                'has_prev': page > 1
            },
            'filters': filter_options,
            'applied_filters': filters
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching inventory: {e}")
        return APIResponse.error("Failed to fetch inventory", 500)


@bp.route('/inventory/<int:item_id>', methods=['GET'])
@login_required_with_status
def get_inventory_item(item_id):
    """Get specific inventory item with complete details and history"""
    try:
        item = InventoryItem.query.get_or_404(item_id)
        
        # Get item data with all details
        item_data = item.to_dict(include_donor=True, include_stats=True)
        
        # TODO: Add transaction history when transaction model is implemented
        # For now, return basic item data
        item_data['transaction_history'] = []
        item_data['current_borrowers'] = []
        item_data['waitlist'] = []
        
        return APIResponse.success({'item': item_data})
        
    except Exception as e:
        current_app.logger.error(f"Error fetching inventory item {item_id}: {e}")
        return APIResponse.error("Failed to fetch inventory item", 500)


@bp.route('/inventory', methods=['POST'])
@role_required('Admin', 'Incharge')
def create_inventory_item():
    """Create new inventory item"""
    try:
        # Validate input
        schema = InventoryItemSchema()
        data = schema.load(request.get_json())
        
        # Check for duplicate SKU if provided
        if data.get('sku_code'):
            existing_item = InventoryItem.get_by_sku(data['sku_code'])
            if existing_item:
                return APIResponse.error("Item with this SKU already exists", 400)
        
        # Set available quantity equal to total quantity initially
        data['available_quantity'] = data['total_quantity']
        
        # Convert item_type string to enum
        data['item_type'] = ItemType(data['item_type'])
        
        # Create inventory item
        item = InventoryItem(**data)
        db.session.add(item)
        db.session.commit()
        
        # Invalidate cache
        invalidate_inventory_cache()
        
        # Audit log
        audit_action(
            actor_id=current_user.id,
            action='INVENTORY_ITEM_CREATED',
            target_type='inventory_item',
            target_id=item.id,
            details={
                'title': item.title,
                'item_type': item.item_type.value,
                'quantity': item.total_quantity,
                'donor_id': item.donor_id
            }
        )
        
        return APIResponse.success(
            {'item': item.to_dict(include_donor=True)},
            f"Inventory item '{item.title}' created successfully",
            201
        )
        
    except ValidationError as e:
        return APIResponse.validation_error(e.messages)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating inventory item: {e}")
        return APIResponse.error("Failed to create inventory item", 500)


@bp.route('/inventory/<int:item_id>', methods=['PUT'])
@role_required('Admin', 'Incharge')
def update_inventory_item(item_id):
    """Update inventory item"""
    try:
        item = InventoryItem.query.get_or_404(item_id)
        
        # Validate input
        schema = InventoryItemSchema()
        data = schema.load(request.get_json())
        
        # Check for duplicate SKU if changed
        if data.get('sku_code') and data['sku_code'] != item.sku_code:
            existing_item = InventoryItem.get_by_sku(data['sku_code'])
            if existing_item:
                return APIResponse.error("Item with this SKU already exists", 400)
        
        # Store old values for audit
        old_values = item.to_dict()
        
        # Handle quantity changes carefully
        old_total = item.total_quantity
        new_total = data['total_quantity']
        borrowed_count = item.get_borrowed_count()
        
        if new_total < borrowed_count:
            return APIResponse.error(
                f"Cannot reduce total quantity below borrowed count ({borrowed_count})", 400
            )
        
        # Update available quantity proportionally
        if new_total != old_total:
            data['available_quantity'] = new_total - borrowed_count
        
        # Convert item_type string to enum if present
        if 'item_type' in data:
            data['item_type'] = ItemType(data['item_type'])
        
        # Update item
        for key, value in data.items():
            setattr(item, key, value)
        
        item.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Audit log
        audit_action(
            actor_id=current_user.id,
            action='INVENTORY_ITEM_UPDATED',
            target_type='inventory_item',
            target_id=item.id,
            details={'old_values': old_values, 'new_values': item.to_dict()}
        )
        
        return APIResponse.success(
            {'item': item.to_dict(include_donor=True)},
            f"Inventory item '{item.title}' updated successfully"
        )
        
    except ValidationError as e:
        return APIResponse.validation_error(e.messages)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating inventory item {item_id}: {e}")
        return APIResponse.error("Failed to update inventory item", 500)


@bp.route('/inventory/<int:item_id>', methods=['DELETE'])
@role_required('Admin')
def delete_inventory_item(item_id):
    """Delete inventory item (Admin only)"""
    try:
        item = InventoryItem.query.get_or_404(item_id)
        
        # Check if item has active transactions
        if item.get_borrowed_count() > 0:
            return APIResponse.error(
                "Cannot delete item with active transactions", 400
            )
        
        item_title = item.title
        db.session.delete(item)
        db.session.commit()
        
        # Audit log
        audit_action(
            actor_id=current_user.id,
            action='INVENTORY_ITEM_DELETED',
            target_type='inventory_item',
            target_id=item_id,
            details={'title': item_title}
        )
        
        return APIResponse.success(
            message=f"Inventory item '{item_title}' deleted successfully"
        )
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting inventory item {item_id}: {e}")
        return APIResponse.error("Failed to delete inventory item", 500)


# Search and discovery endpoints
@bp.route('/search', methods=['GET'])
@login_required_with_status
def search():
    """Universal search endpoint with suggestions"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query or len(query) < 2:
            return APIResponse.error("Query must be at least 2 characters", 400)
        
        # Get search suggestions
        suggestions = SearchService.get_search_suggestions(query, limit=10)
        
        return APIResponse.success({
            'query': query,
            'suggestions': suggestions
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in search: {e}")
        return APIResponse.error("Search failed", 500)


@bp.route('/search/popular', methods=['GET'])
@login_required_with_status
def popular_searches():
    """Get popular searches and trending items"""
    try:
        popular_data = SearchService.get_popular_searches()
        return APIResponse.success(popular_data)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching popular searches: {e}")
        return APIResponse.error("Failed to fetch popular searches", 500)


# Analytics endpoints for inventory
@bp.route('/inventory/analytics', methods=['GET'])
@role_required('Admin', 'Incharge', 'Volunteer')
def inventory_analytics():
    """Get inventory analytics and statistics"""
    try:
        # Basic inventory statistics
        total_items = InventoryItem.query.count()
        available_items = InventoryItem.query.filter(
            InventoryItem.available_quantity > 0
        ).count()
        
        # Items by type
        items_by_type = {}
        for item_type in ItemType:
            count = InventoryItem.query.filter_by(item_type=item_type).count()
            items_by_type[item_type.value] = count
        
        # Popular items
        popular_items = InventoryItem.get_popular_items(limit=5)
        popular_data = [item.to_dict(include_donor=True) for item in popular_items]
        
        # Recent additions
        recent_items = InventoryItem.get_recent_additions(limit=5)
        recent_data = [item.to_dict(include_donor=True) for item in recent_items]
        
        return APIResponse.success({
            'summary': {
                'total_items': total_items,
                'available_items': available_items,
                'unavailable_items': total_items - available_items,
                'availability_rate': (available_items / total_items * 100) if total_items > 0 else 0
            },
            'items_by_type': items_by_type,
            'popular_items': popular_data,
            'recent_additions': recent_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching inventory analytics: {e}")
        return APIResponse.error("Failed to fetch analytics", 500)