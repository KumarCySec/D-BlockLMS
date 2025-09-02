"""
Performance monitoring and query logging utilities
"""
import time
import logging
from functools import wraps
from flask import current_app, g, request
from sqlalchemy import event
from sqlalchemy.engine import Engine


class PerformanceMonitor:
    """Performance monitoring service"""
    
    def __init__(self):
        self.slow_query_threshold = 1.0  # 1 second
        self.logger = logging.getLogger('performance')
        
    def setup_query_logging(self, app):
        """Setup SQLAlchemy query performance logging"""
        
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time"""
            context._query_start_time = time.time()
            
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log query performance"""
            total_time = time.time() - context._query_start_time
            
            # Log slow queries
            if total_time > self.slow_query_threshold:
                self.logger.warning(
                    f"Slow query detected: {total_time:.3f}s - {statement[:200]}..."
                )
            
            # Store in app context for request-level aggregation
            if hasattr(g, 'query_times'):
                g.query_times.append(total_time)
                g.query_count += 1
            else:
                g.query_times = [total_time]
                g.query_count = 1
    
    def log_request_performance(self):
        """Log overall request performance"""
        if hasattr(g, 'query_times') and g.query_times:
            total_query_time = sum(g.query_times)
            avg_query_time = total_query_time / len(g.query_times)
            
            if total_query_time > self.slow_query_threshold:
                self.logger.info(
                    f"Request performance - Path: {request.path}, "
                    f"Queries: {g.query_count}, "
                    f"Total query time: {total_query_time:.3f}s, "
                    f"Avg query time: {avg_query_time:.3f}s"
                )


def monitor_performance(func_name=None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                
                # Log if execution time exceeds threshold
                if execution_time > 0.5:  # 500ms threshold
                    name = func_name or func.__name__
                    current_app.logger.info(
                        f"Performance: {name} took {execution_time:.3f}s"
                    )
        
        return wrapper
    return decorator


def log_search_performance(search_type, query, filters, execution_time, result_count):
    """Log search operation performance"""
    logger = logging.getLogger('search_performance')
    
    log_data = {
        'type': search_type,
        'query': query[:100] if query else None,  # Truncate long queries
        'filters': len(filters) if filters else 0,
        'execution_time': round(execution_time, 3),
        'result_count': result_count,
        'endpoint': request.endpoint if request else None
    }
    
    # Log slow searches
    if execution_time > 1.0:
        logger.warning(f"Slow search: {log_data}")
    else:
        logger.info(f"Search performance: {log_data}")


class QueryAnalyzer:
    """Analyze and provide recommendations for query optimization"""
    
    @staticmethod
    def analyze_inventory_search(query, filters, execution_time):
        """Analyze inventory search performance and provide recommendations"""
        recommendations = []
        
        # Check for full-text search opportunities
        if query and execution_time > 0.5:
            recommendations.append(
                "Consider using full-text search indexes for better text search performance"
            )
        
        # Check for missing indexes
        if filters and execution_time > 1.0:
            if 'item_type' in filters:
                recommendations.append("Ensure item_type column has an index")
            if 'department_id' in filters:
                recommendations.append("Ensure department_id column has an index")
            if 'availability' in filters:
                recommendations.append("Ensure available_quantity column has an index")
        
        # Check for complex joins
        if filters and ('donor_batch' in filters or 'donor_branch' in filters):
            if execution_time > 0.8:
                recommendations.append(
                    "Consider denormalizing donor batch/branch data for better performance"
                )
        
        return recommendations
    
    @staticmethod
    def analyze_donor_search(query, filters, execution_time):
        """Analyze donor search performance"""
        recommendations = []
        
        if query and execution_time > 0.3:
            recommendations.append(
                "Consider adding full-text search index on donor name and notes"
            )
        
        if execution_time > 0.5:
            recommendations.append("Review donor table indexes for optimization")
        
        return recommendations


def setup_performance_monitoring(app):
    """Setup performance monitoring for the application"""
    monitor = PerformanceMonitor()
    
    # Setup query logging
    monitor.setup_query_logging(app)
    
    # Setup request-level performance logging
    @app.before_request
    def before_request():
        g.start_time = time.time()
    
    @app.after_request
    def after_request(response):
        # Log request performance
        if hasattr(g, 'start_time'):
            request_time = time.time() - g.start_time
            
            # Log slow requests
            if request_time > 2.0:  # 2 second threshold
                current_app.logger.warning(
                    f"Slow request: {request.method} {request.path} - {request_time:.3f}s"
                )
        
        # Log query performance
        monitor.log_request_performance()
        
        return response
    
    return app


# Performance metrics collection
class PerformanceMetrics:
    """Collect and store performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'search_operations': [],
            'api_requests': [],
            'slow_queries': []
        }
    
    def record_search_operation(self, search_type, execution_time, result_count):
        """Record search operation metrics"""
        self.metrics['search_operations'].append({
            'type': search_type,
            'execution_time': execution_time,
            'result_count': result_count,
            'timestamp': time.time()
        })
        
        # Keep only recent metrics (last 1000 operations)
        if len(self.metrics['search_operations']) > 1000:
            self.metrics['search_operations'] = self.metrics['search_operations'][-1000:]
    
    def record_api_request(self, endpoint, method, execution_time, status_code):
        """Record API request metrics"""
        self.metrics['api_requests'].append({
            'endpoint': endpoint,
            'method': method,
            'execution_time': execution_time,
            'status_code': status_code,
            'timestamp': time.time()
        })
        
        # Keep only recent metrics
        if len(self.metrics['api_requests']) > 1000:
            self.metrics['api_requests'] = self.metrics['api_requests'][-1000:]
    
    def get_performance_summary(self):
        """Get performance summary statistics"""
        now = time.time()
        hour_ago = now - 3600  # 1 hour
        
        # Recent search operations
        recent_searches = [
            op for op in self.metrics['search_operations']
            if op['timestamp'] > hour_ago
        ]
        
        # Recent API requests
        recent_requests = [
            req for req in self.metrics['api_requests']
            if req['timestamp'] > hour_ago
        ]
        
        summary = {
            'search_operations': {
                'count': len(recent_searches),
                'avg_time': sum(op['execution_time'] for op in recent_searches) / len(recent_searches) if recent_searches else 0,
                'slow_count': len([op for op in recent_searches if op['execution_time'] > 1.0])
            },
            'api_requests': {
                'count': len(recent_requests),
                'avg_time': sum(req['execution_time'] for req in recent_requests) / len(recent_requests) if recent_requests else 0,
                'error_count': len([req for req in recent_requests if req['status_code'] >= 400])
            }
        }
        
        return summary


# Global performance metrics instance
performance_metrics = PerformanceMetrics()