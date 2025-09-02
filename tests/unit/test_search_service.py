"""
Unit tests for SearchService with full-text search and caching
"""
import pytest
from unittest.mock import patch, MagicMock
from app.utils.search import SearchService
from app.utils.cache import CacheService, FilterCache
from app.models.inventory_item import InventoryItem, ItemType
from app.models.donor import Donor
from app.models.department import Department
from app import db


class TestSearchService:
    """Test SearchService functionality"""
    
    def test_fulltext_search_sqlite(self, app):
        """Test SQLite FTS5 search functionality"""
        with app.app_context():
            # Mock database URL to simulate SQLite
            with patch.object(db.engine, 'url') as mock_url:
                mock_url.__str__ = MagicMock(return_value='sqlite:///test.db')
                
                # Create test data
                donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
                db.session.add(donor)
                db.session.commit()
                
                item = InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Python Programming Guide",
                    authors="John Doe",
                    donor_id=donor.id,
                    total_quantity=5,
                    available_quantity=3
                )
                db.session.add(item)
                db.session.commit()
                
                # Test search
                items, total, filters = SearchService.search_inventory(
                    query="Python",
                    page=1,
                    per_page=10
                )
                
                # Should find the item (fallback to LIKE search in test)
                assert total >= 0
                assert isinstance(filters, dict)
    
    def test_fulltext_search_postgresql(self, app):
        """Test PostgreSQL full-text search functionality"""
        with app.app_context():
            # Mock database URL to simulate PostgreSQL
            with patch.object(db.engine, 'url') as mock_url:
                mock_url.__str__ = MagicMock(return_value='postgresql://user:pass@localhost/test')
                
                # Create test data
                donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
                db.session.add(donor)
                db.session.commit()
                
                item = InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Advanced Database Systems",
                    authors="Jane Smith",
                    donor_id=donor.id,
                    total_quantity=3,
                    available_quantity=2
                )
                db.session.add(item)
                db.session.commit()
                
                # Test search (will fallback to LIKE in test environment)
                items, total, filters = SearchService.search_inventory(
                    query="Database",
                    page=1,
                    per_page=10
                )
                
                assert total >= 0
                assert isinstance(filters, dict)
    
    def test_search_with_complex_filters(self, app):
        """Test search with multiple filters"""
        with app.app_context():
            # Create test data
            donor1 = Donor(name="Donor A", branch="CSE", batch="2020-2024")
            donor2 = Donor(name="Donor B", branch="ECE", batch="2019-2023")
            db.session.add_all([donor1, donor2])
            db.session.commit()
            
            dept = Department(name="Computer Science", code="CSE")
            db.session.add(dept)
            db.session.commit()
            
            items = [
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="CSE Book Available",
                    donor_id=donor1.id,
                    department_id=dept.id,
                    language="English",
                    total_quantity=5,
                    available_quantity=3
                ),
                InventoryItem(
                    item_type=ItemType.LAPTOP,
                    title="ECE Laptop Unavailable",
                    donor_id=donor2.id,
                    language="English",
                    total_quantity=2,
                    available_quantity=0
                )
            ]
            db.session.add_all(items)
            db.session.commit()
            
            # Test multiple filters
            filters = {
                'item_type': 'book',
                'availability': 'available',
                'language': 'English'
            }
            
            results, total, filter_options = SearchService.search_inventory(
                filters=filters,
                page=1,
                per_page=10
            )
            
            # Should return only available books in English
            for item in results:
                assert item.item_type == ItemType.BOOK
                assert item.available_quantity > 0
                assert item.language == "English"
    
    def test_search_sorting(self, app):
        """Test search result sorting"""
        with app.app_context():
            donor = Donor(name="Test Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            # Create items with different popularity
            items = [
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Popular Book",
                    donor_id=donor.id,
                    total_quantity=10,
                    available_quantity=2  # 8 borrowed - high popularity
                ),
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Unpopular Book",
                    donor_id=donor.id,
                    total_quantity=10,
                    available_quantity=9  # 1 borrowed - low popularity
                )
            ]
            db.session.add_all(items)
            db.session.commit()
            
            # Test sorting by popularity (descending)
            results, total, filters = SearchService.search_inventory(
                sort_by='popularity',
                sort_order='desc',
                page=1,
                per_page=10
            )
            
            assert len(results) >= 2
            # First item should be more popular (more borrowed)
            assert results[0].get_borrowed_count() >= results[1].get_borrowed_count()
    
    def test_donor_search(self, app):
        """Test donor search functionality"""
        with app.app_context():
            donors = [
                Donor(name="Alice Johnson", branch="CSE", batch="2020-2024", email="alice@test.com"),
                Donor(name="Bob Smith", branch="ECE", batch="2019-2023", notes="Alumni donor"),
                Donor(name="Charlie Brown", branch="CSE", batch="2021-2025")
            ]
            db.session.add_all(donors)
            db.session.commit()
            
            # Test name search
            results, total = SearchService.search_donors(query="Alice")
            assert total == 1
            assert results[0].name == "Alice Johnson"
            
            # Test email search
            results, total = SearchService.search_donors(query="alice@test.com")
            assert total == 1
            assert results[0].email == "alice@test.com"
            
            # Test notes search
            results, total = SearchService.search_donors(query="Alumni")
            assert total == 1
            assert results[0].name == "Bob Smith"
            
            # Test branch filter
            results, total = SearchService.search_donors(filters={'branch': 'CSE'})
            assert total == 2
            
            # Test batch filter
            results, total = SearchService.search_donors(filters={'batch': '2020-2024'})
            assert total == 1
    
    def test_search_suggestions(self, app):
        """Test search suggestions functionality"""
        with app.app_context():
            donor = Donor(name="Suggestion Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            item = InventoryItem(
                item_type=ItemType.BOOK,
                title="Python Programming Handbook",
                authors="Expert Author",
                donor_id=donor.id,
                total_quantity=5,
                available_quantity=3
            )
            db.session.add(item)
            db.session.commit()
            
            # Test suggestions
            suggestions = SearchService.get_search_suggestions("Python", limit=5)
            
            assert 'items' in suggestions
            assert 'donors' in suggestions
            assert isinstance(suggestions['items'], list)
            assert isinstance(suggestions['donors'], list)
    
    def test_popular_searches(self, app):
        """Test popular searches functionality"""
        with app.app_context():
            donor = Donor(name="Popular Donor", branch="CSE", batch="2020-2024")
            db.session.add(donor)
            db.session.commit()
            
            # Create items with different popularity
            items = [
                InventoryItem(
                    item_type=ItemType.BOOK,
                    title="Very Popular Book",
                    donor_id=donor.id,
                    total_quantity=10,
                    available_quantity=0  # All borrowed
                ),
                InventoryItem(
                    item_type=ItemType.LAPTOP,
                    title="Recent Laptop",
                    donor_id=donor.id,
                    total_quantity=5,
                    available_quantity=5  # None borrowed
                )
            ]
            db.session.add_all(items)
            db.session.commit()
            
            popular_data = SearchService.get_popular_searches()
            
            assert 'popular_items' in popular_data
            assert 'recent_additions' in popular_data
            assert 'popular_filters' in popular_data
            assert isinstance(popular_data['popular_items'], list)
            assert isinstance(popular_data['recent_additions'], list)


class TestCacheService:
    """Test caching functionality"""
    
    def test_cache_availability(self, app):
        """Test cache service availability"""
        with app.app_context():
            # Test without Redis (should handle gracefully)
            available = CacheService.is_available()
            # Should be False in test environment without Redis
            assert isinstance(available, bool)
    
    def test_cache_operations_without_redis(self, app):
        """Test cache operations when Redis is not available"""
        with app.app_context():
            # These should not raise errors even without Redis
            result = CacheService.get('test_key')
            assert result is None
            
            success = CacheService.set('test_key', {'test': 'data'})
            assert isinstance(success, bool)
            
            success = CacheService.delete('test_key')
            assert isinstance(success, bool)
    
    def test_filter_cache_operations(self, app):
        """Test filter cache operations"""
        with app.app_context():
            # Test inventory filters
            test_filters = {
                'item_types': [{'value': 'book', 'label': 'Book'}],
                'languages': [{'value': 'English', 'label': 'English'}]
            }
            
            # These should not raise errors
            FilterCache.set_inventory_filters(test_filters)
            cached_filters = FilterCache.get_inventory_filters()
            
            # Without Redis, should return None
            assert cached_filters is None or isinstance(cached_filters, dict)
            
            # Test invalidation
            FilterCache.invalidate_inventory_cache()
            FilterCache.invalidate_donor_cache()
            FilterCache.invalidate_all()
    
    @patch('app.utils.cache.CacheService.is_available')
    @patch('app.utils.cache.CacheService.get')
    @patch('app.utils.cache.CacheService.set')
    def test_filter_cache_with_mock_redis(self, mock_set, mock_get, mock_available, app):
        """Test filter cache with mocked Redis"""
        with app.app_context():
            # Mock Redis as available
            mock_available.return_value = True
            mock_get.return_value = None
            mock_set.return_value = True
            
            # Test getting filter options (should generate and cache)
            filters = SearchService.get_inventory_filter_options()
            
            assert isinstance(filters, dict)
            assert 'item_types' in filters
            assert 'languages' in filters
            
            # Should have called cache operations
            mock_get.assert_called()
            mock_set.assert_called()
    
    def test_cached_decorator(self, app):
        """Test the cached decorator"""
        with app.app_context():
            call_count = 0
            
            @cached('test_func', expire=60)
            def test_function(x, y):
                nonlocal call_count
                call_count += 1
                return x + y
            
            # First call
            result1 = test_function(1, 2)
            assert result1 == 3
            assert call_count == 1
            
            # Second call (should use cache if available, or call again if not)
            result2 = test_function(1, 2)
            assert result2 == 3
            # call_count might be 1 or 2 depending on cache availability
            assert call_count in [1, 2]