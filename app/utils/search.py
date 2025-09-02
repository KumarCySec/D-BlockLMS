"""
Search utilities for inventory and donor management
"""
from typing import Dict, List, Optional, Tuple
from sqlalchemy import text, or_, and_, desc, asc
from flask import current_app
from app import db
from app.models.inventory_item import InventoryItem, ItemType
from app.models.donor import Donor
from app.models.department import Department
from app.utils.cache import FilterCache, cached


class SearchService:
    """Service for handling search and filtering operations"""
    
    @staticmethod
    def _apply_fulltext_search(query_obj, search_query: str, search_type: str):
        """Apply full-text search based on database type"""
        try:
            # Check database type
            db_url = str(db.engine.url)
            
            if 'sqlite' in db_url:
                return SearchService._apply_sqlite_fts(query_obj, search_query, search_type)
            elif 'postgresql' in db_url:
                return SearchService._apply_postgresql_fts(query_obj, search_query, search_type)
            else:
                # Fallback to LIKE search for other databases
                return SearchService._apply_like_search(query_obj, search_query, search_type)
                
        except Exception as e:
            current_app.logger.warning(f"Full-text search failed, falling back to LIKE: {e}")
            return SearchService._apply_like_search(query_obj, search_query, search_type)
    
    @staticmethod
    def _apply_sqlite_fts(query_obj, search_query: str, search_type: str):
        """Apply SQLite FTS5 search"""
        if search_type == 'inventory':
            # Use FTS5 virtual table for inventory search
            fts_query = text("""
                SELECT inventory_item.* FROM inventory_item
                JOIN inventory_fts ON inventory_item.id = inventory_fts.id
                WHERE inventory_fts MATCH :search_query
                ORDER BY rank
            """)
            
            # Execute FTS query and get IDs
            result = db.session.execute(fts_query, {'search_query': search_query})
            item_ids = [row[0] for row in result]
            
            if item_ids:
                query_obj = query_obj.filter(InventoryItem.id.in_(item_ids))
            else:
                # No FTS results, fallback to LIKE search
                return SearchService._apply_like_search(query_obj, search_query, search_type)
                
        elif search_type == 'donor':
            # Use FTS5 virtual table for donor search
            fts_query = text("""
                SELECT donor.* FROM donor
                JOIN donor_fts ON donor.id = donor_fts.id
                WHERE donor_fts MATCH :search_query
                ORDER BY rank
            """)
            
            result = db.session.execute(fts_query, {'search_query': search_query})
            donor_ids = [row[0] for row in result]
            
            if donor_ids:
                query_obj = query_obj.filter(Donor.id.in_(donor_ids))
            else:
                return SearchService._apply_like_search(query_obj, search_query, search_type)
        
        return query_obj
    
    @staticmethod
    def _apply_postgresql_fts(query_obj, search_query: str, search_type: str):
        """Apply PostgreSQL full-text search with GIN indexes"""
        # Convert search query to tsquery format
        ts_query = ' & '.join(search_query.split())
        
        if search_type == 'inventory':
            query_obj = query_obj.filter(
                or_(
                    text("to_tsvector('english', title) @@ to_tsquery('english', :query)"),
                    text("to_tsvector('english', authors) @@ to_tsquery('english', :query)"),
                    text("to_tsvector('english', description) @@ to_tsquery('english', :query)")
                ).params(query=ts_query)
            )
        elif search_type == 'donor':
            query_obj = query_obj.filter(
                or_(
                    text("to_tsvector('english', name) @@ to_tsquery('english', :query)"),
                    text("to_tsvector('english', notes) @@ to_tsquery('english', :query)")
                ).params(query=ts_query)
            )
        
        return query_obj
    
    @staticmethod
    def _apply_like_search(query_obj, search_query: str, search_type: str):
        """Fallback LIKE search for databases without full-text search"""
        search_term = f"%{search_query}%"
        
        if search_type == 'inventory':
            query_obj = query_obj.filter(
                or_(
                    InventoryItem.title.ilike(search_term),
                    InventoryItem.authors.ilike(search_term),
                    InventoryItem.description.ilike(search_term),
                    InventoryItem.sku_code.ilike(search_term)
                )
            )
        elif search_type == 'donor':
            query_obj = query_obj.filter(
                or_(
                    Donor.name.ilike(search_term),
                    Donor.email.ilike(search_term),
                    Donor.notes.ilike(search_term)
                )
            )
        
        return query_obj
    
    @staticmethod
    def search_inventory(
        query: Optional[str] = None,
        filters: Optional[Dict] = None,
        sort_by: str = 'title',
        sort_order: str = 'asc',
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[InventoryItem], int, Dict]:
        """
        Advanced inventory search with filtering, sorting, and pagination
        
        Returns:
            Tuple of (items, total_count, filter_options)
        """
        query_obj = InventoryItem.query
        
        # Apply text search using full-text search when available
        if query and query.strip():
            query_obj = SearchService._apply_fulltext_search(query_obj, query.strip(), 'inventory')
        
        # Apply filters
        if filters:
            query_obj = SearchService._apply_inventory_filters(query_obj, filters)
        
        # Get total count before pagination
        total_count = query_obj.count()
        
        # Apply sorting
        query_obj = SearchService._apply_sorting(query_obj, sort_by, sort_order)
        
        # Apply pagination
        offset = (page - 1) * per_page
        items = query_obj.offset(offset).limit(per_page).all()
        
        # Get filter options for UI
        filter_options = SearchService.get_inventory_filter_options()
        
        return items, total_count, filter_options
    
    @staticmethod
    def _apply_inventory_filters(query_obj, filters: Dict):
        """Apply filters to inventory query"""
        
        if filters.get('item_type'):
            if isinstance(filters['item_type'], list):
                # Multiple item types
                item_types = [ItemType(t) for t in filters['item_type']]
                query_obj = query_obj.filter(InventoryItem.item_type.in_(item_types))
            else:
                query_obj = query_obj.filter(InventoryItem.item_type == ItemType(filters['item_type']))
        
        if filters.get('language'):
            if isinstance(filters['language'], list):
                query_obj = query_obj.filter(InventoryItem.language.in_(filters['language']))
            else:
                query_obj = query_obj.filter(InventoryItem.language == filters['language'])
        
        if filters.get('department'):
            if isinstance(filters['department'], list):
                query_obj = query_obj.filter(InventoryItem.department_id.in_(filters['department']))
            else:
                query_obj = query_obj.filter(InventoryItem.department_id == filters['department'])
        
        if filters.get('donor'):
            if isinstance(filters['donor'], list):
                query_obj = query_obj.filter(InventoryItem.donor_id.in_(filters['donor']))
            else:
                query_obj = query_obj.filter(InventoryItem.donor_id == filters['donor'])
        
        if filters.get('availability'):
            if filters['availability'] == 'available':
                query_obj = query_obj.filter(InventoryItem.available_quantity > 0)
            elif filters['availability'] == 'unavailable':
                query_obj = query_obj.filter(InventoryItem.available_quantity == 0)
            elif filters['availability'] == 'all':
                pass  # No filter
        
        if filters.get('donor_batch'):
            query_obj = query_obj.join(Donor).filter(Donor.batch == filters['donor_batch'])
        
        if filters.get('donor_branch'):
            query_obj = query_obj.join(Donor).filter(Donor.branch == filters['donor_branch'])
        
        return query_obj
    
    @staticmethod
    def _apply_sorting(query_obj, sort_by: str, sort_order: str):
        """Apply sorting to query"""
        
        # Define sort columns
        sort_columns = {
            'title': InventoryItem.title,
            'authors': InventoryItem.authors,
            'created_at': InventoryItem.created_at,
            'date_added': InventoryItem.created_at,
            'availability': InventoryItem.available_quantity,
            'popularity': (InventoryItem.total_quantity - InventoryItem.available_quantity),
            'donor_batch': None,  # Requires join
            'type': InventoryItem.item_type
        }
        
        if sort_by == 'donor_batch':
            # Special case for donor batch sorting
            query_obj = query_obj.join(Donor)
            sort_column = Donor.batch
        else:
            sort_column = sort_columns.get(sort_by, InventoryItem.title)
        
        # Apply sort order
        if sort_order == 'desc':
            query_obj = query_obj.order_by(desc(sort_column))
        else:
            query_obj = query_obj.order_by(asc(sort_column))
        
        # Add secondary sort by title for consistency
        if sort_by != 'title':
            query_obj = query_obj.order_by(asc(InventoryItem.title))
        
        return query_obj
    
    @staticmethod
    def get_inventory_filter_options() -> Dict:
        """Get available filter options for inventory search with caching"""
        
        # Try to get from cache first
        cached_filters = FilterCache.get_inventory_filters()
        if cached_filters is not None:
            return cached_filters
        
        # Generate filter options
        filter_options = SearchService._generate_inventory_filter_options()
        
        # Cache the results
        FilterCache.set_inventory_filters(filter_options)
        
        return filter_options
    
    @staticmethod
    def _generate_inventory_filter_options() -> Dict:
        """Generate inventory filter options from database"""
        
        # Item types
        item_types = [{'value': item_type.value, 'label': item_type.value.title()} 
                     for item_type in ItemType]
        
        # Languages
        languages_query = db.session.query(InventoryItem.language.distinct()).filter(
            InventoryItem.language.isnot(None),
            InventoryItem.language != ''
        ).all()
        languages = [{'value': lang[0], 'label': lang[0]} 
                    for lang in languages_query if lang[0]]
        languages.sort(key=lambda x: x['label'])
        
        # Departments
        departments_query = db.session.query(
            Department.id, Department.name
        ).join(InventoryItem).distinct().all()
        departments = [{'value': dept[0], 'label': dept[1]} 
                      for dept in departments_query]
        departments.sort(key=lambda x: x['label'])
        
        # Donors
        donors_query = db.session.query(
            Donor.id, Donor.name, Donor.batch
        ).join(InventoryItem).distinct().all()
        donors = [{'value': donor[0], 'label': f"{donor[1]} ({donor[2]})"} 
                 for donor in donors_query]
        donors.sort(key=lambda x: x['label'])
        
        # Donor batches
        batches_query = db.session.query(Donor.batch.distinct()).join(
            InventoryItem
        ).order_by(desc(Donor.batch)).all()
        batches = [{'value': batch[0], 'label': batch[0]} 
                  for batch in batches_query if batch[0]]
        
        # Donor branches
        branches_query = db.session.query(Donor.branch.distinct()).join(
            InventoryItem
        ).order_by(Donor.branch).all()
        branches = [{'value': branch[0], 'label': branch[0]} 
                   for branch in branches_query if branch[0]]
        
        return {
            'item_types': item_types,
            'languages': languages,
            'departments': departments,
            'donors': donors,
            'donor_batches': batches,
            'donor_branches': branches,
            'availability_options': [
                {'value': 'all', 'label': 'All Items'},
                {'value': 'available', 'label': 'Available Only'},
                {'value': 'unavailable', 'label': 'Unavailable Only'}
            ],
            'sort_options': [
                {'value': 'title', 'label': 'Title'},
                {'value': 'authors', 'label': 'Author'},
                {'value': 'created_at', 'label': 'Date Added'},
                {'value': 'popularity', 'label': 'Popularity'},
                {'value': 'availability', 'label': 'Availability'},
                {'value': 'donor_batch', 'label': 'Donor Batch'},
                {'value': 'type', 'label': 'Item Type'}
            ]
        }
    
    @staticmethod
    def search_donors(
        query: Optional[str] = None,
        filters: Optional[Dict] = None,
        sort_by: str = 'name',
        sort_order: str = 'asc',
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Donor], int]:
        """
        Search donors with filtering and pagination
        
        Returns:
            Tuple of (donors, total_count)
        """
        query_obj = Donor.query
        
        # Apply text search using full-text search when available
        if query and query.strip():
            query_obj = SearchService._apply_fulltext_search(query_obj, query.strip(), 'donor')
        
        # Apply filters
        if filters:
            if filters.get('branch'):
                query_obj = query_obj.filter(Donor.branch == filters['branch'])
            
            if filters.get('batch'):
                query_obj = query_obj.filter(Donor.batch == filters['batch'])
        
        # Get total count
        total_count = query_obj.count()
        
        # Apply sorting
        sort_columns = {
            'name': Donor.name,
            'branch': Donor.branch,
            'batch': Donor.batch,
            'created_at': Donor.created_at
        }
        
        sort_column = sort_columns.get(sort_by, Donor.name)
        if sort_order == 'desc':
            query_obj = query_obj.order_by(desc(sort_column))
        else:
            query_obj = query_obj.order_by(asc(sort_column))
        
        # Apply pagination
        offset = (page - 1) * per_page
        donors = query_obj.offset(offset).limit(per_page).all()
        
        return donors, total_count
    
    @staticmethod
    def get_search_suggestions(query: str, limit: int = 5) -> Dict:
        """Get search suggestions for autocomplete"""
        if not query or len(query) < 2:
            return {'items': [], 'donors': []}
        
        search_term = f"%{query}%"
        
        # Item suggestions
        item_suggestions = db.session.query(
            InventoryItem.title, InventoryItem.authors
        ).filter(
            or_(
                InventoryItem.title.ilike(search_term),
                InventoryItem.authors.ilike(search_term)
            )
        ).limit(limit).all()
        
        items = []
        for item in item_suggestions:
            if item.title and query.lower() in item.title.lower():
                items.append({'type': 'title', 'text': item.title})
            if item.authors and query.lower() in item.authors.lower():
                items.append({'type': 'author', 'text': item.authors})
        
        # Donor suggestions
        donor_suggestions = db.session.query(Donor.name).filter(
            Donor.name.ilike(search_term)
        ).limit(limit).all()
        
        donors = [{'type': 'donor', 'text': donor.name} 
                 for donor in donor_suggestions]
        
        return {
            'items': items[:limit],
            'donors': donors[:limit]
        }
    
    @staticmethod
    def get_popular_searches() -> Dict:
        """Get popular search terms and filters with caching"""
        
        # Try to get from cache first
        cached_searches = FilterCache.get_popular_searches()
        if cached_searches is not None:
            return cached_searches
        
        # Generate popular searches
        popular_searches = SearchService._generate_popular_searches()
        
        # Cache the results
        FilterCache.set_popular_searches(popular_searches)
        
        return popular_searches
    
    @staticmethod
    def _generate_popular_searches() -> Dict:
        """Generate popular searches from database"""
        
        popular_items = InventoryItem.query.order_by(
            desc(InventoryItem.total_quantity - InventoryItem.available_quantity)
        ).limit(5).all()
        
        recent_items = InventoryItem.query.order_by(
            desc(InventoryItem.created_at)
        ).limit(5).all()
        
        return {
            'popular_items': [item.title for item in popular_items],
            'recent_additions': [item.title for item in recent_items],
            'popular_filters': [
                {'type': 'item_type', 'value': 'book', 'label': 'Books'},
                {'type': 'availability', 'value': 'available', 'label': 'Available Items'},
                {'type': 'item_type', 'value': 'laptop', 'label': 'Laptops'}
            ]
        }