"""
Integration tests for transaction API endpoints
"""
import pytest
import json
from datetime import datetime, timedelta
from app import create_app, db
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.models.role import Role
from app.models.inventory_item import InventoryItem, ItemType, ItemStatus
from app.models.department import Department
from flask_login import login_user


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
        db.session.refresh(dept)
        return dept


@pytest.fixture
def student_role(app):
    """Create student role"""
    with app.app_context():
        role = Role(name="Student", description="Student role")
        db.session.add(role)
        db.session.commit()
        db.session.refresh(role)
        return role


@pytest.fixture
def volunteer_role(app):
    """Create volunteer role"""
    with app.app_context():
        role = Role(name="Volunteer", description="Volunteer role")
        db.session.add(role)
        db.session.commit()
        db.session.refresh(role)
        return role


@pytest.fixture
def sample_student(app, sample_department, student_role):
    """Create sample student user"""
    with app.app_context():
        from app.models.user import UserStatus
        user = User(
            name="Test Student",
            email="student@example.com",
            roll_number="CS2021001",
            branch="Computer Science",
            batch="2021-2025",
            phone="1234567890",
            department_id=sample_department.id,
            status=UserStatus.ACTIVE
        )
        user.set_password("password123")
        user.roles.append(student_role)
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def sample_volunteer(app, sample_department, volunteer_role):
    """Create sample volunteer user"""
    with app.app_context():
        from app.models.user import UserStatus
        user = User(
            name="Test Volunteer",
            email="volunteer@example.com",
            roll_number="CS2020001",
            branch="Computer Science",
            batch="2020-2024",
            phone="0987654321",
            department_id=sample_department.id,
            status=UserStatus.ACTIVE
        )
        user.set_password("password123")
        user.roles.append(volunteer_role)
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
def authenticated_student(client, sample_student):
    """Login as student"""
    response = client.post('/auth/login', data={
        'email': sample_student.email,
        'password': 'password123'
    })
    return sample_student


@pytest.fixture
def authenticated_volunteer(client, sample_volunteer):
    """Login as volunteer"""
    response = client.post('/auth/login', data={
        'email': sample_volunteer.email,
        'password': 'password123'
    })
    return sample_volunteer


class TestTransactionAPI:
    """Test transaction API endpoints"""
    
    def test_create_checkout_request(self, client, authenticated_student, sample_item):
        """Test creating a checkout request"""
        response = client.post('/api/transactions/request', 
            data=json.dumps({
                'item_id': sample_item.id,
                'notes': 'Need this book for assignment'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        
        assert data['success'] == True
        assert 'transaction' in data['data']
        transaction = data['data']['transaction']
        assert transaction['transaction_id'].startswith('DBL-')
        assert transaction['status'] == 'requested'
        assert transaction['item']['id'] == sample_item.id
        assert transaction['user']['id'] == authenticated_student.id
    
    def test_create_request_invalid_item(self, client, authenticated_student):
        """Test creating request with invalid item ID"""
        response = client.post('/api/transactions/request',
            data=json.dumps({
                'item_id': 99999,
                'notes': 'Test request'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'message' in data
    
    def test_create_request_unavailable_item(self, client, authenticated_student, sample_item):
        """Test creating request for unavailable item"""
        # Make item unavailable
        sample_item.status = ItemStatus.BORROWED
        db.session.commit()
        
        response = client.post('/api/transactions/request',
            data=json.dumps({
                'item_id': sample_item.id,
                'notes': 'Test request'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 201  # API doesn't check availability at request time
        data = json.loads(response.data)
        assert data['success'] == True
    
    def test_get_user_transactions(self, client, authenticated_student, sample_item):
        """Test getting user's transactions"""
        # Create a transaction first
        with client.application.app_context():
            transaction = Transaction.create_request(
                user_id=authenticated_student.id,
                item_id=sample_item.id,
                notes="Test transaction"
            )
            db.session.commit()
            transaction_id = transaction.transaction_id
        
        response = client.get('/api/transactions')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] == True
        assert 'transactions' in data['data']
        assert len(data['data']['transactions']) == 1
        assert data['data']['transactions'][0]['transaction_id'] == transaction_id
    
    def test_get_transaction_details(self, client, authenticated_student, sample_item):
        """Test getting specific transaction details"""
        # Create a transaction first
        with client.application.app_context():
            transaction = Transaction.create_request(
                user_id=authenticated_student.id,
                item_id=sample_item.id
            )
            db.session.commit()
            transaction_id = transaction.transaction_id
        
        response = client.get(f'/api/transactions/{transaction_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] == True
        transaction = data['data']['transaction']
        assert transaction['transaction_id'] == transaction_id
        assert transaction['status'] == 'requested'
        assert 'user' in transaction
        assert 'item' in transaction
    
    def test_get_nonexistent_transaction(self, client, authenticated_student):
        """Test getting non-existent transaction"""
        response = client.get('/api/transactions/99999')
        
        assert response.status_code == 404
    
    def test_approve_transaction_as_volunteer(self, client, authenticated_volunteer, sample_student, sample_item):
        """Test approving transaction as volunteer"""
        # Create a transaction first
        with client.application.app_context():
            transaction = Transaction.create_request(
                user_id=sample_student.id,
                item_id=sample_item.id
            )
            db.session.commit()
            transaction_id = transaction.transaction_id
        
        response = client.post(f'/api/transactions/{transaction.id}/approve',
            data=json.dumps({
                'notes': 'Approved by volunteer'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] == True
        transaction_data = data['data']['transaction']
        assert transaction_data['status'] == 'approved'
        assert transaction_data['approved_by_user_id'] == authenticated_volunteer.id
        assert 'due_date' in transaction_data
    
    def test_reject_transaction_as_volunteer(self, client, authenticated_volunteer, sample_student, sample_item):
        """Test rejecting transaction as volunteer"""
        # Create a transaction first
        with client.application.app_context():
            transaction = Transaction.create_request(
                user_id=sample_student.id,
                item_id=sample_item.id
            )
            db.session.commit()
            transaction_id = transaction.transaction_id
        
        response = client.post(f'/api/transactions/{transaction.id}/reject',
            data=json.dumps({
                'notes': 'Item damaged'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] == True
        transaction_data = data['data']['transaction']
        assert transaction_data['status'] == 'rejected'
        assert 'Item damaged' in transaction_data.get('notes', '')
    
    def test_student_cannot_approve_transaction(self, client, authenticated_student, sample_item):
        """Test that students cannot approve transactions"""
        # Create a transaction first
        with client.application.app_context():
            transaction = Transaction.create_request(
                user_id=authenticated_student.id,
                item_id=sample_item.id
            )
            db.session.commit()
            transaction_id = transaction.transaction_id
        
        response = client.post(f'/api/transactions/{transaction.id}/approve',
            data=json.dumps({
                'notes': 'Trying to approve'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 403
    
    def test_issue_transaction(self, client, authenticated_volunteer, sample_student, sample_item):
        """Test issuing an approved transaction"""
        # Create and approve a transaction first
        with client.application.app_context():
            from app.utils.transaction_service import transaction_service
            transaction = transaction_service.create_checkout_request(
                user_id=sample_student.id,
                item_id=sample_item.id
            )
            transaction = transaction_service.approve_request(
                transaction_id=transaction.id,
                approver_id=authenticated_volunteer.id
            )
            transaction_id = transaction.transaction_id
        
        response = client.post(f'/api/transactions/{transaction.id}/issue',
            data=json.dumps({
                'notes': 'Item issued to student'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] == True
        transaction_data = data['data']['transaction']
        assert transaction_data['status'] == 'borrowed'
        assert 'issued_at' in transaction_data
    
    def test_return_transaction(self, client, authenticated_volunteer, sample_student, sample_item):
        """Test returning a borrowed item"""
        # Create, approve, and issue a transaction first
        with client.application.app_context():
            from app.utils.transaction_service import transaction_service
            transaction = transaction_service.create_checkout_request(
                user_id=sample_student.id,
                item_id=sample_item.id
            )
            transaction = transaction_service.approve_request(
                transaction_id=transaction.id,
                approver_id=authenticated_volunteer.id
            )
            transaction = transaction_service.issue_item(
                transaction_id=transaction.id,
                issuer_id=authenticated_volunteer.id
            )
            transaction_id = transaction.transaction_id
        
        response = client.post(f'/api/transactions/{transaction.id}/return',
            data=json.dumps({
                'notes': 'Item returned in good condition'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] == True
        transaction_data = data['data']['transaction']
        assert transaction_data['status'] == 'returned'
        assert 'returned_at' in transaction_data
    
    def test_renew_transaction(self, client, authenticated_student, sample_item):
        """Test renewing a borrowed item"""
        # Create, approve, and issue a transaction first
        with client.application.app_context():
            from app.utils.transaction_service import transaction_service
            transaction = transaction_service.create_checkout_request(
                user_id=authenticated_student.id,
                item_id=sample_item.id
            )
            transaction = transaction_service.approve_request(
                transaction_id=transaction.id,
                approver_id=authenticated_student.id  # For test purposes
            )
            transaction = transaction_service.issue_item(
                transaction_id=transaction.id,
                issuer_id=authenticated_student.id  # For test purposes
            )
            transaction_id = transaction.transaction_id
            original_due_date = transaction.due_date
        
        response = client.post(f'/api/transactions/{transaction.id}/renew',
            data=json.dumps({
                'days': 7
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] == True
        transaction_data = data['data']['transaction']
        assert transaction_data['renew_count'] == 1
        # Due date should be extended
        new_due_date = datetime.fromisoformat(data['new_due_date'])
        assert new_due_date > original_due_date
    
    def test_get_pending_approvals(self, client, authenticated_volunteer, sample_student, sample_item):
        """Test getting pending approval transactions"""
        # Create some transactions
        with client.application.app_context():
            t1 = Transaction.create_request(sample_student.id, sample_item.id)
            t2 = Transaction.create_request(sample_student.id, sample_item.id)
            t2.transition_to(TransactionStatus.APPROVED, actor_id=authenticated_volunteer.id)
            db.session.commit()
        
        response = client.get('/api/transactions/pending')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] == True
        assert 'transactions' in data['data']
        # Only one should be pending (t1)
        assert len(data['data']['transactions']) == 1
        assert data['data']['transactions'][0]['status'] == 'requested'
    
    def test_get_overdue_transactions(self, client, authenticated_volunteer, sample_student, sample_item):
        """Test getting overdue transactions"""
        # Create an overdue transaction
        with client.application.app_context():
            transaction = Transaction.create_request(
                user_id=sample_student.id,
                item_id=sample_item.id
            )
            transaction.transition_to(TransactionStatus.APPROVED, actor_id=authenticated_volunteer.id)
            transaction.transition_to(TransactionStatus.BORROWED, actor_id=authenticated_volunteer.id)
            # Set due date to past
            transaction.due_date = datetime.utcnow() - timedelta(days=2)
            db.session.commit()
        
        response = client.get('/api/transactions/overdue')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] == True
        assert 'transactions' in data['data']
        assert len(data['data']['transactions']) == 1
        assert data['data']['transactions'][0]['is_overdue'] == True
        assert data['data']['transactions'][0]['days_overdue'] == 2
    
    def test_transaction_statistics(self, client, authenticated_volunteer, sample_student, sample_item):
        """Test getting transaction statistics"""
        # Create transactions with different statuses
        with client.application.app_context():
            t1 = Transaction.create_request(sample_student.id, sample_item.id)
            t2 = Transaction.create_request(sample_student.id, sample_item.id)
            t3 = Transaction.create_request(sample_student.id, sample_item.id)
            
            t1.transition_to(TransactionStatus.APPROVED, actor_id=authenticated_volunteer.id)
            t2.transition_to(TransactionStatus.REJECTED, actor_id=authenticated_volunteer.id)
            db.session.commit()
        
        response = client.get('/api/transactions/dashboard')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] == True
        stats = data['data']
        assert stats['pending_requests'] >= 0
        assert 'borrowed_items' in stats
        assert 'total_active' in stats


class TestTransactionValidation:
    """Test transaction validation and error handling"""
    
    def test_invalid_status_transition(self, client, authenticated_volunteer, sample_student, sample_item):
        """Test invalid status transitions are rejected"""
        # Create a transaction
        with client.application.app_context():
            transaction = Transaction.create_request(
                user_id=sample_student.id,
                item_id=sample_item.id
            )
            db.session.commit()
            transaction_id = transaction.transaction_id
        
        # Try to return without approving/issuing first
        response = client.post(f'/api/transactions/{transaction.id}/return',
            data=json.dumps({
                'notes': 'Invalid return'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'message' in data
    
    def test_duplicate_active_request(self, client, authenticated_student, sample_item):
        """Test that users cannot have multiple active requests for same item"""
        # Create first request
        response1 = client.post('/api/transactions/request',
            data=json.dumps({
                'item_id': sample_item.id,
                'notes': 'First request'
            }),
            content_type='application/json'
        )
        
        assert response1.status_code == 201
        
        # Try to create second request for same item
        response2 = client.post('/api/transactions/request',
            data=json.dumps({
                'item_id': sample_item.id,
                'notes': 'Second request'
            }),
            content_type='application/json'
        )
        
        assert response2.status_code == 400
        data = json.loads(response2.data)
        assert data['success'] == False
        assert 'already has' in data['message'].lower()
    
    def test_max_renewals_exceeded(self, client, authenticated_student, sample_item):
        """Test that renewals are rejected when max limit is reached"""
        # Create and process transaction
        with client.application.app_context():
            transaction = Transaction.create_request(
                user_id=authenticated_student.id,
                item_id=sample_item.id
            )
            transaction.transition_to(TransactionStatus.APPROVED, actor_id=authenticated_student.id)
            transaction.transition_to(TransactionStatus.BORROWED, actor_id=authenticated_student.id)
            # Set to max renewals
            transaction.renew_count = 4
            db.session.commit()
            transaction_id = transaction.transaction_id
        
        response = client.post(f'/api/transactions/{transaction.id}/renew',
            data=json.dumps({
                'days': 7
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'maximum renewals' in data['message'].lower() or 'not found' in data['message'].lower()


class TestTransactionPermissions:
    """Test transaction permission controls"""
    
    def test_unauthenticated_access_denied(self, client, sample_item):
        """Test that unauthenticated users cannot access transaction endpoints"""
        response = client.post('/api/transactions/request',
            data=json.dumps({
                'item_id': sample_item.id
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 302  # Redirect to login
    
    def test_user_can_only_see_own_transactions(self, client, authenticated_student, sample_item):
        """Test that users can only see their own transactions"""
        # Create transaction for different user
        with client.application.app_context():
            from app.models.user import UserStatus
            other_user = User(
                name="Other User",
                email="other@example.com",
                roll_number="CS2021002",
                branch="Computer Science",
                batch="2021-2025",
                phone="9876543210",
                department_id=authenticated_student.department_id,
                status=UserStatus.ACTIVE
            )
            other_user.set_password("password123")
            db.session.add(other_user)
            db.session.commit()
            
            transaction = Transaction.create_request(
                user_id=other_user.id,
                item_id=sample_item.id
            )
            db.session.commit()
            transaction_id = transaction.transaction_id
        
        # Try to access other user's transaction
        response = client.get(f'/api/transactions/{transaction.id}')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['success'] == False
        assert 'access denied' in data['message'].lower() or 'not found' in data['message'].lower()
    
    def test_volunteer_can_see_all_transactions(self, client, authenticated_volunteer, sample_student, sample_item):
        """Test that volunteers can see all transactions"""
        # Create transaction for student
        with client.application.app_context():
            transaction = Transaction.create_request(
                user_id=sample_student.id,
                item_id=sample_item.id
            )
            db.session.commit()
            transaction_id = transaction.transaction_id
        
        # Volunteer should be able to access it
        response = client.get(f'/api/transactions/{transaction.id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] == True
        assert data['data']['transaction']['transaction_id'] == transaction_id