"""
Unit tests for inventory and donor models
"""
import pytest
from datetime import datetime, date
from app.models.inventory_item import InventoryItem, ItemType
from app.models.donor import Donor
from app.models.department import Department
from app import db


class TestDonorModel:
    """Test Donor model functionality"""
    
    def test_create_donor(self, app):
        """Test donor creation with required fields"""
        with app.app_context():
            donor = Donor(
                name="John Doe",
                branch="CSE",
                batch="2020-2024"
            )
            
            assert donor.name == "John Doe"
            assert donor.branch == "CSE"
            assert donor.batch == "2020-2024"
            assert donor.address is None
            assert donor.phone is None
            assert donor.email is None
    
    def test_donor_with_optional_fields(self, app):
        """Test donor creation with all fields"""
        with app.app_context():
            donor = Donor(
                name="Jane Smith",
                branch="ECE",
                batch="2019-2023",
                address="123 Main St, City",
                phone="9876543210",
                email="jane@example.com",
                notes="Alumni donor"
            )
            
            db.session.add(donor)
            db.session.commit()
            
            assert donor.id is not None
            assert donor.name == "Jane Smith"
            assert donor.address == "123 Main St, City"
            assert donor.phone == "9876543210"
            assert donor.email == "jane@example.com"
            assert donor.notes == "Alumni donor"
            assert donor.created_at is not None
            assert donor.updated_at is not None
    
    def test_donor_repr(self, app):
        """Test donor string representation"""
        with app.app_context():
            donor = Donor(name="Test User", branch="CSE", batch="2020-2024")
            assert str(donor) == "<Donor Test User (2020-2024)>"
    
    def test_donor_to_dict(self, app):
        """Test donor dictionary conversion"""
        with app.app_context():
            donor = Donor(
                name="Test User",
                branch="CSE",
                batch="2020-2024",
                email="test@example.com"
            )
            db.session.add(donor)
            db.session.commit()
            
            data = donor.to_dict()
            
            assert data['name'] == "Test User"
            assert data['branch'] == "CSE"
            assert data['batch'] == "2020-2024"
            assert data['email'] == "test@example.com"
            assert 'created_at' in data
            assert 'updated_at' in data
    
    def test_donor_to_dict_with_stats(self, app):
        """Test donor dictionary with statistics"""
        with app.app_context():
            donor = Donor(name="Test User", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            # Add inventory item
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                donor_id=donor.id,
                total_quantity=5,
                available_quantity=3
            )
            db.session.add(item)
            db.session.commit()
            
            data = donor.to_dict(include_stats=True)
            
            assert data['donation_count'] == 1
            assert data['total_quantity'] == 5
            assert 'donations_by_type' in data
            assert data['donations_by_type']['book'] == 5
    
    def test_donor_search(self, app):
        """Test donor search functionality"""
        with app.app_context():
            # Create test donors
            donor1 = Donor(name="Alice Johnson", branch="CSE", batch="2020-2024")
            donor2 = Donor(name="Bob Smith", branch="ECE", batch="2019-2023")
            donor3 = Donor(name="Charlie Brown", branch="CSE", batch="2021-2025")
            
            db.session.add_all([donor1, donor2, donor3])
            db.session.commit()
            
            # Test name search
            results = Donor.search_donors(query="Alice")
            assert len(results) == 1
            assert results[0].name == "Alice Johnson"
            
            # Test branch filter
            results = Donor.search_donors(branch="CSE")
            assert len(results) == 2
            
            # Test batch filter
            results = Donor.search_donors(batch="2020-2024")
            assert len(results) == 1
            
            # Test combined filters
            results = Donor.search_donors(branch="CSE", batch="2021-2025")
            assert len(results) == 1
            assert results[0].name == "Charlie Brown"
    
    def test_get_by_email(self, app):
        """Test get donor by email"""
        with app.app_context():
            donor = Donor(
                name="Test User",
                branch="CSE",
                batch="2020-2024",
                email="unique@example.com"
            )
            db.session.add(donor)
            db.session.commit()
            
            found_donor = Donor.get_by_email("unique@example.com")
            assert found_donor is not None
            assert found_donor.name == "Test User"
            
            not_found = Donor.get_by_email("nonexistent@example.com")
            assert not_found is None
    
    def test_get_branches_and_batches(self, app):
        """Test getting unique branches and batches"""
        with app.app_context():
            donors = [
                Donor(name="User1", branch="CSE", batch="2020-2024"),
                Donor(name="User2", branch="ECE", batch="2019-2023"),
                Donor(name="User3", branch="CSE", batch="2021-2025"),
            ]
            
            db.session.add_all(donors)
            db.session.commit()
            
            branches = Donor.get_branches()
            assert "CSE" in branches
            assert "ECE" in branches
            
            batches = Donor.get_batches()
            assert "2020-2024" in batches
            assert "2019-2023" in batches
            assert "2021-2025" in batches
    
    def test_donor_field_validation(self, app):
        """Test donor field validation and constraints"""
        with app.app_context():
            # Test required fields
            donor = Donor(
                name="Valid Donor",
                branch="CSE",
                batch="2020-2024"
            )
            db.session.add(donor)
            db.session.commit()
            
            assert donor.id is not None
            assert donor.name == "Valid Donor"
            assert donor.branch == "CSE"
            assert donor.batch == "2020-2024"
            
            # Test optional fields
            donor_with_all_fields = Donor(
                name="Complete Donor",
                branch="ECE",
                batch="2019-2023",
                address="123 Test Street, Test City",
                phone="9876543210",
                email="complete@test.com",
                notes="Test notes for donor"
            )
            db.session.add(donor_with_all_fields)
            db.session.commit()
            
            assert donor_with_all_fields.address == "123 Test Street, Test City"
            assert donor_with_all_fields.phone == "9876543210"
            assert donor_with_all_fields.email == "complete@test.com"
            assert donor_with_all_fields.notes == "Test notes for donor"
    
    def test_donor_statistics_methods(self, app):
        """Test donor statistics calculation methods"""
        with app.app_context():
            donor = Donor(name="Stats Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            # Initially no donations
            assert donor.get_donation_count() == 0
            assert donor.get_total_quantity_donated() == 0
            assert donor.get_donations_by_type() == {}
            
            # Add inventory items
            items = [
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Book 1",
                    donor_id=donor.id,
                    total_quantity=5,
                    available_quantity=3
                ),
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Book 2",
                    donor_id=donor.id,
                    total_quantity=3,
                    available_quantity=2
                ),
                InventoryItem(
                    item_type=ItemType.LAPTOP,
                    title="Laptop 1",
                    donor_id=donor.id,
                    total_quantity=2,
                    available_quantity=1
                )
            ]
            db.session.add_all(items)
            db.session.commit()
            
            # Test statistics
            assert donor.get_donation_count() == 3
            assert donor.get_total_quantity_donated() == 10  # 5 + 3 + 2
            
            donations_by_type = donor.get_donations_by_type()
            assert donations_by_type['book'] == 8  # 5 + 3
            assert donations_by_type['laptop'] == 2
    
    def test_donor_search_edge_cases(self, app):
        """Test edge cases in donor search functionality"""
        with app.app_context():
            # Create donors with special characters and cases
            donors = [
                Donor(name="O'Connor", branch="CSE", batch="2020-2024", email="oconnor@test.com"),
                Donor(name="Smith-Jones", branch="ECE", batch="2019-2023"),
                Donor(name="José García", branch="CSE", batch="2021-2025", notes="International student"),
            ]
            db.session.add_all(donors)
            db.session.commit()
            
            # Test search with apostrophe
            results = Donor.search_donors(query="O'Connor")
            assert len(results) == 1
            assert results[0].name == "O'Connor"
            
            # Test search with hyphen
            results = Donor.search_donors(query="Smith-Jones")
            assert len(results) == 1
            assert results[0].name == "Smith-Jones"
            
            # Test search with accented characters
            results = Donor.search_donors(query="José")
            assert len(results) == 1
            assert results[0].name == "José García"
            
            # Test search in notes
            results = Donor.search_donors(query="International")
            assert len(results) == 1
            assert results[0].name == "José García"
            
            # Test case insensitive search
            results = Donor.search_donors(query="garcia")
            assert len(results) == 1
            assert results[0].name == "José García"
    
    def test_donor_data_integrity(self, app):
        """Test donor data integrity and relationships"""
        with app.app_context():
            donor = Donor(
                name="Integrity Test",
                branch="CSE",
                batch="2020-2024",
                email="integrity@test.com"
            )
            db.session.add(donor)
            db.session.commit()
            
            # Test timestamps are set
            assert donor.created_at is not None
            assert donor.updated_at is not None
            assert donor.created_at == donor.updated_at
            
            # Test update timestamp changes
            original_updated_at = donor.updated_at
            donor.notes = "Updated notes"
            db.session.commit()
            
            # Refresh from database
            db.session.refresh(donor)
            assert donor.updated_at > original_updated_at
            
            # Test relationship integrity
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Relationship Test",
                donor_id=donor.id,
                total_quantity=1,
                available_quantity=1
            )
            db.session.add(item)
            db.session.commit()
            
            # Test bidirectional relationship
            assert item in donor.donated_items
            assert item.donor == donor


class TestInventoryItemModel:
    """Test InventoryItem model functionality"""
    
    def test_create_inventory_item(self, app):
        """Test inventory item creation"""
        with app.app_context():
            # Create donor first
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                authors="Test Author",
                language="English",
                donor_id=donor.id,
                total_quantity=10,
                available_quantity=8
            )
            
            assert item.item_type == ItemType.BOOK
            assert item.title == "Test Book"
            assert item.authors == "Test Author"
            assert item.language == "English"
            assert item.total_quantity == 10
            assert item.available_quantity == 8
    
    def test_inventory_item_with_department(self, app):
        """Test inventory item with department association"""
        with app.app_context():
            # Get or create department and donor
            dept = Department.get_by_code("CSE")
            if not dept:
                dept = Department(name="Computer Science Engineering", code="CSE")
                db.session.add(dept)
            
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            item = InventoryItem(
                item_type=ItemType.LAPTOP,
                title="Dell Laptop",
                donor_id=donor.id,
                department_id=dept.id,
                total_quantity=5,
                available_quantity=5
            )
            
            db.session.add(item)
            db.session.commit()
            
            assert item.department_id == dept.id
            assert item.department.name == "Computer Science Engineering"
    
    def test_item_type_enum(self, app):
        """Test ItemType enum values"""
        assert ItemType.BOOK.value == 'book'
        assert ItemType.LAPTOP.value == 'laptop'
        assert ItemType.KIT.value == 'kit'
        
        # Test enum in model
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            book = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                donor_id=donor.id,
                total_quantity=1,
                available_quantity=1
            )
            
            laptop = InventoryItem(
                item_type=ItemType.LAPTOP,
                title="Test Laptop",
                donor_id=donor.id,
                total_quantity=1,
                available_quantity=1
            )
            
            kit = InventoryItem(
                item_type=ItemType.KIT,
                title="Test Kit",
                donor_id=donor.id,
                total_quantity=1,
                available_quantity=1
            )
            
            db.session.add_all([book, laptop, kit])
            db.session.commit()
            
            assert book.item_type == ItemType.BOOK
            assert laptop.item_type == ItemType.LAPTOP
            assert kit.item_type == ItemType.KIT
    
    def test_availability_methods(self, app):
        """Test availability checking methods"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            # Available item
            available_item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Available Book",
                donor_id=donor.id,
                total_quantity=10,
                available_quantity=5
            )
            
            # Unavailable item
            unavailable_item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Unavailable Book",
                donor_id=donor.id,
                total_quantity=10,
                available_quantity=0
            )
            
            assert available_item.is_available() is True
            assert unavailable_item.is_available() is False
            
            assert available_item.get_borrowed_count() == 5
            assert unavailable_item.get_borrowed_count() == 10
    
    def test_update_availability_atomic(self, app):
        """Test atomic availability updates"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                donor_id=donor.id,
                total_quantity=10,
                available_quantity=8
            )
            
            # Valid decrease
            result = item.update_availability(-2)
            assert result is True
            assert item.available_quantity == 6
            
            # Valid increase
            result = item.update_availability(3)
            assert result is True
            assert item.available_quantity == 9
            
            # Invalid decrease (would go negative)
            with pytest.raises(ValueError, match="Available quantity cannot be negative"):
                item.update_availability(-15)
            
            # Invalid increase (would exceed total)
            with pytest.raises(ValueError, match="Available quantity cannot exceed total quantity"):
                item.update_availability(5)
    
    def test_popularity_score(self, app):
        """Test popularity score calculation"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            # Fully available item (0% borrowed)
            item1 = InventoryItem(
                item_type=ItemType.BOOK,
                title="Unpopular Book",
                donor_id=donor.id,
                total_quantity=10,
                available_quantity=10
            )
            
            # Half borrowed item (50% borrowed)
            item2 = InventoryItem(
                item_type=ItemType.BOOK,
                title="Popular Book",
                donor_id=donor.id,
                total_quantity=10,
                available_quantity=5
            )
            
            # Fully borrowed item (100% borrowed)
            item3 = InventoryItem(
                item_type=ItemType.BOOK,
                title="Very Popular Book",
                donor_id=donor.id,
                total_quantity=10,
                available_quantity=0
            )
            
            assert item1.get_popularity_score() == 0.0
            assert item2.get_popularity_score() == 0.5
            assert item3.get_popularity_score() == 1.0
    
    def test_to_dict_conversion(self, app):
        """Test inventory item dictionary conversion"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            
            # Get or create department
            dept = Department.get_by_code("CSE")
            if not dept:
                dept = Department(name="Computer Science Engineering", code="CSE")
                db.session.add(dept)
            
            db.session.add(donor)
            db.session.commit()
            
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                authors="Test Author",
                language="English",
                published_date=date(2023, 1, 1),
                sku_code="BOOK001",
                description="A test book",
                donor_id=donor.id,
                department_id=dept.id,
                total_quantity=10,
                available_quantity=7
            )
            
            db.session.add(item)
            db.session.commit()
            
            # Basic conversion
            data = item.to_dict()
            
            assert data['item_type'] == 'book'
            assert data['title'] == 'Test Book'
            assert data['authors'] == 'Test Author'
            assert data['language'] == 'English'
            assert data['published_date'] == '2023-01-01'
            assert data['sku_code'] == 'BOOK001'
            assert data['description'] == 'A test book'
            assert data['total_quantity'] == 10
            assert data['available_quantity'] == 7
            assert data['is_available'] is True
            assert data['department_name'] == 'Computer Science Engineering'
            
            # With donor info
            assert 'donor' in data
            assert data['donor']['name'] == 'Test Donor'
            
            # With stats
            stats_data = item.to_dict(include_stats=True)
            assert 'borrowed_count' in stats_data
            assert 'popularity_score' in stats_data
            assert stats_data['borrowed_count'] == 3
            assert stats_data['popularity_score'] == 0.3
    
    def test_search_items(self, app):
        """Test inventory item search functionality"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            # Create test items
            items = [
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Python Programming",
                    authors="John Doe",
                    language="English",
                    donor_id=donor.id,
                    total_quantity=5,
                    available_quantity=3
                ),
                InventoryItem(
                    item_type=ItemType.LAPTOP,
                    title="Dell Laptop",
                    authors="Dell Inc",
                    language="English",
                    donor_id=donor.id,
                    total_quantity=2,
                    available_quantity=0
                ),
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Java Fundamentals",
                    authors="Jane Smith",
                    language="English",
                    donor_id=donor.id,
                    total_quantity=3,
                    available_quantity=3
                )
            ]
            
            db.session.add_all(items)
            db.session.commit()
            
            # Test text search
            results = InventoryItem.search_items(query="Python")
            assert len(results) == 1
            assert results[0].title == "Python Programming"
            
            # Test type filter
            results = InventoryItem.search_items(filters={'item_type': 'book'})
            assert len(results) == 2
            
            # Test availability filter
            results = InventoryItem.search_items(filters={'availability': 'available'})
            assert len(results) == 2  # Only items with available_quantity > 0
            
            results = InventoryItem.search_items(filters={'availability': 'unavailable'})
            assert len(results) == 1
            assert results[0].title == "Dell Laptop"
    
    def test_get_by_sku(self, app):
        """Test getting item by SKU code"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                sku_code="UNIQUE001",
                donor_id=donor.id,
                total_quantity=1,
                available_quantity=1
            )
            
            db.session.add(item)
            db.session.commit()
            
            found_item = InventoryItem.get_by_sku("UNIQUE001")
            assert found_item is not None
            assert found_item.title == "Test Book"
            
            not_found = InventoryItem.get_by_sku("NONEXISTENT")
            assert not_found is None
    
    def test_get_available_items(self, app):
        """Test getting available items with filters"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            
            # Get or create department
            dept = Department.get_by_code("CSE")
            if not dept:
                dept = Department(name="Computer Science Engineering", code="CSE")
                db.session.add(dept)
            
            db.session.add(donor)
            db.session.commit()
            
            items = [
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Available Book",
                    donor_id=donor.id,
                    department_id=dept.id,
                    total_quantity=5,
                    available_quantity=3
                ),
                InventoryItem(
                    item_type=ItemType.LAPTOP,
                    title="Available Laptop",
                    donor_id=donor.id,
                    department_id=dept.id,
                    total_quantity=2,
                    available_quantity=1
                ),
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Unavailable Book",
                    donor_id=donor.id,
                    department_id=dept.id,
                    total_quantity=3,
                    available_quantity=0
                )
            ]
            
            db.session.add_all(items)
            db.session.commit()
            
            # Get all available items
            available = InventoryItem.get_available_items()
            assert len(available) == 2
            
            # Filter by type
            available_books = InventoryItem.get_available_items(item_type='book')
            assert len(available_books) == 1
            assert available_books[0].title == "Available Book"
            
            # Filter by department
            dept_items = InventoryItem.get_available_items(department_id=dept.id)
            assert len(dept_items) == 2
    
    def test_inventory_item_repr(self, app):
        """Test inventory item string representation"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                donor_id=donor.id,
                total_quantity=1,
                available_quantity=1
            )
            
            assert str(item) == "<InventoryItem Test Book (book)>"
    
    def test_inventory_item_validation_constraints(self, app):
        """Test inventory item field validation and constraints"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            # Test negative quantities
            with pytest.raises(ValueError):
                item = InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Test Book",
                    donor_id=donor.id,
                    total_quantity=5,
                    available_quantity=3
                )
                item.update_availability(-10)  # Would make available negative
            
            # Test exceeding total quantity
            with pytest.raises(ValueError):
                item = InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Test Book",
                    donor_id=donor.id,
                    total_quantity=5,
                    available_quantity=3
                )
                item.update_availability(5)  # Would exceed total
    
    def test_inventory_item_relationships(self, app):
        """Test inventory item relationships with donor and department"""
        with app.app_context():
            # Create donor
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            
            # Create department
            dept = Department(name="Computer Science", code="CSE")
            db.session.add(dept)
            db.session.commit()
            
            # Create item with relationships
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                donor_id=donor.id,
                department_id=dept.id,
                total_quantity=5,
                available_quantity=3
            )
            db.session.add(item)
            db.session.commit()
            
            # Test relationships
            assert item.donor == donor
            assert item.department == dept
            assert item in donor.donated_items
            assert item in dept.inventory_items
    
    def test_inventory_item_atomic_updates(self, app):
        """Test atomic updates for inventory quantities"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Test Book",
                donor_id=donor.id,
                total_quantity=10,
                available_quantity=8
            )
            db.session.add(item)
            db.session.commit()
            
            # Test successful atomic update
            original_updated_at = item.updated_at
            result = item.update_availability(-2)
            
            assert result is True
            assert item.available_quantity == 6
            assert item.updated_at > original_updated_at
            
            # Test rollback on error
            try:
                item.update_availability(-10)  # Should fail
            except ValueError:
                pass
            
            # Quantity should remain unchanged after failed update
            assert item.available_quantity == 6
    
    def test_inventory_item_search_edge_cases(self, app):
        """Test edge cases in inventory item search"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            # Create items with special characters and edge cases
            items = [
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="C++ Programming",
                    authors="Bjarne Stroustrup",
                    donor_id=donor.id,
                    total_quantity=1,
                    available_quantity=1
                ),
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Data Structures & Algorithms",
                    authors="Thomas H. Cormen",
                    donor_id=donor.id,
                    total_quantity=1,
                    available_quantity=0
                )
            ]
            db.session.add_all(items)
            db.session.commit()
            
            # Test search with special characters
            results = InventoryItem.search_items(query="C++")
            assert len(results) == 1
            assert results[0].title == "C++ Programming"
            
            # Test search with ampersand
            results = InventoryItem.search_items(query="&")
            assert len(results) == 1
            assert results[0].title == "Data Structures & Algorithms"
            
            # Test empty query
            results = InventoryItem.search_items(query="")
            assert len(results) >= 2  # Should return all items
            
            # Test case insensitive search
            results = InventoryItem.search_items(query="programming")
            assert len(results) == 1
            assert results[0].title == "C++ Programming"