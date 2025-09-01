"""
Scheduled task utilities for background operations
"""
from datetime import datetime, timedelta
from flask import current_app
from app.models.audit_log import AuditLog


class ScheduledTasks:
    """Scheduled task management"""
    
    @staticmethod
    def cleanup_audit_logs():
        """Clean up old audit logs based on retention policy"""
        try:
            retention_days = current_app.config.get('AUDIT_LOG_RETENTION_DAYS', 365)
            
            if current_app.config.get('AUDIT_LOG_CLEANUP_ENABLED', True):
                deleted_count = AuditLog.cleanup_old_logs(retention_days)
                
                # Log the cleanup operation
                AuditLog.log_action(
                    action='SYSTEM_MAINTENANCE',
                    description=f"Audit log cleanup completed: {deleted_count} entries removed",
                    severity='INFO',
                    metadata={
                        'retention_days': retention_days,
                        'deleted_count': deleted_count,
                        'cleanup_time': datetime.utcnow().isoformat()
                    }
                )
                
                current_app.logger.info(f"Audit log cleanup: removed {deleted_count} entries")
                return deleted_count
            
        except Exception as e:
            current_app.logger.error(f"Audit log cleanup failed: {e}")
            
            # Log the failure
            AuditLog.log_action(
                action='SYSTEM_ERROR',
                description=f"Audit log cleanup failed: {str(e)}",
                severity='ERROR',
                metadata={'error': str(e)}
            )
            
            return 0
    
    @staticmethod
    def check_audit_log_size():
        """Check if audit log size exceeds maximum and force cleanup if needed"""
        try:
            max_entries = current_app.config.get('AUDIT_LOG_MAX_ENTRIES', 1000000)
            current_count = AuditLog.query.count()
            
            if current_count > max_entries:
                # Force cleanup of oldest entries
                excess_count = current_count - max_entries
                
                # Delete oldest entries
                oldest_logs = AuditLog.query.order_by(AuditLog.created_at.asc()).limit(excess_count)
                for log in oldest_logs:
                    from app import db
                    db.session.delete(log)
                
                db.session.commit()
                
                # Log the forced cleanup
                AuditLog.log_action(
                    action='SYSTEM_MAINTENANCE',
                    description=f"Forced audit log cleanup: {excess_count} entries removed due to size limit",
                    severity='WARNING',
                    metadata={
                        'max_entries': max_entries,
                        'current_count': current_count,
                        'removed_count': excess_count
                    }
                )
                
                current_app.logger.warning(f"Forced audit log cleanup: removed {excess_count} entries")
                return excess_count
            
            return 0
            
        except Exception as e:
            current_app.logger.error(f"Audit log size check failed: {e}")
            return 0
    
    @staticmethod
    def generate_security_report():
        """Generate daily security report from audit logs"""
        try:
            # Get security events from last 24 hours
            security_events = AuditLog.get_security_events(24)
            
            # Count failed logins by IP
            failed_logins = {}
            suspicious_activities = []
            
            for event in security_events:
                if event.action.value == 'failed_login':
                    ip = event.ip_address or 'unknown'
                    failed_logins[ip] = failed_logins.get(ip, 0) + 1
                elif event.action.value == 'suspicious_activity':
                    suspicious_activities.append(event)
            
            # Log security summary
            AuditLog.log_action(
                action='SECURITY_REPORT',
                description=f"Daily security report generated: {len(security_events)} events",
                severity='INFO',
                metadata={
                    'total_security_events': len(security_events),
                    'failed_login_ips': failed_logins,
                    'suspicious_activities_count': len(suspicious_activities),
                    'report_date': datetime.utcnow().date().isoformat()
                }
            )
            
            return {
                'total_events': len(security_events),
                'failed_logins': failed_logins,
                'suspicious_activities': len(suspicious_activities)
            }
            
        except Exception as e:
            current_app.logger.error(f"Security report generation failed: {e}")
            return None


def setup_scheduled_tasks(app):
    """Set up scheduled tasks for the application"""
    
    # This would be used with APScheduler in development
    # In production, these should be run as cron jobs
    
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = BackgroundScheduler()
        
        # Daily audit log cleanup at 2 AM
        scheduler.add_job(
            func=ScheduledTasks.cleanup_audit_logs,
            trigger=CronTrigger(hour=2, minute=0),
            id='audit_cleanup',
            name='Daily audit log cleanup',
            replace_existing=True
        )
        
        # Hourly audit log size check
        scheduler.add_job(
            func=ScheduledTasks.check_audit_log_size,
            trigger=CronTrigger(minute=0),
            id='audit_size_check',
            name='Hourly audit log size check',
            replace_existing=True
        )
        
        # Daily security report at 6 AM
        scheduler.add_job(
            func=ScheduledTasks.generate_security_report,
            trigger=CronTrigger(hour=6, minute=0),
            id='security_report',
            name='Daily security report',
            replace_existing=True
        )
        
        scheduler.start()
        app.logger.info("Scheduled tasks initialized")
        
        # Store scheduler in app context for cleanup
        app.scheduler = scheduler
        
    except ImportError:
        app.logger.info("APScheduler not available, scheduled tasks disabled")
    except Exception as e:
        app.logger.error(f"Failed to initialize scheduled tasks: {e}")


def create_cron_scripts():
    """Create cron job scripts for production deployment"""
    
    # This creates shell scripts that can be used as cron jobs
    scripts = {
        'audit_cleanup.sh': '''#!/bin/bash
# Daily audit log cleanup
cd /path/to/your/app
source venv/bin/activate
flask cleanup-audit-logs --days 365
''',
        
        'security_report.sh': '''#!/bin/bash
# Daily security report
cd /path/to/your/app
source venv/bin/activate
python -c "
from app import create_app
from app.utils.scheduler import ScheduledTasks
app = create_app()
with app.app_context():
    ScheduledTasks.generate_security_report()
"
''',
        
        'audit_size_check.sh': '''#!/bin/bash
# Hourly audit log size check
cd /path/to/your/app
source venv/bin/activate
python -c "
from app import create_app
from app.utils.scheduler import ScheduledTasks
app = create_app()
with app.app_context():
    ScheduledTasks.check_audit_log_size()
"
'''
    }
    
    return scripts


# Cron job schedule recommendations for production:
# 
# # Daily audit cleanup at 2 AM
# 0 2 * * * /path/to/audit_cleanup.sh
# 
# # Hourly audit size check
# 0 * * * * /path/to/audit_size_check.sh
# 
# # Daily security report at 6 AM
# 0 6 * * * /path/to/security_report.sh