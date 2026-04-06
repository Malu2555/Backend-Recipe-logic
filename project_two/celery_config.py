"""
Celery Beat schedule configuration.
Defines all periodic/cron tasks that should be executed automatically.
"""
from celery.schedules import crontab
from datetime import timedelta

# Celery Beat Schedule Configuration
# Define all tasks that should run on a schedule
CELERY_BEAT_SCHEDULE = {
    # Cache cleanup task - runs daily at 2:00 AM UTC
    'cleanup-expired-cache': {
        'task': 'recipes.tasks.cleanup_expired_cache_task',
        'schedule': crontab(hour=2, minute=0),  # Every day at 2:00 AM
        'kwargs': {'days': 30}
    },
    
    # Alternative: Run every 24 hours starting from now
    # 'cleanup-expired-cache': {
    #     'task': 'recipes.tasks.cleanup_expired_cache_task',
    #     'schedule': timedelta(hours=24),
    #     'kwargs': {'days': 30}
    # },
    
    # Cache statistics task - runs daily at 1:00 AM UTC
    'cache-statistics': {
        'task': 'recipes.tasks.generate_cache_stats_task',
        'schedule': crontab(hour=1, minute=0),  # Every day at 1:00 AM
    },
    
    # Example: Run a task every hour
    # 'task-name': {
    #     'task': 'app.tasks.task_function',
    #     'schedule': timedelta(hours=1),
    # },
    
    # Example: Run a task at specific times
    # 'task-name': {
    #     'task': 'app.tasks.task_function',
    #     'schedule': crontab(hour='*/6'),  # Every 6 hours
    # },
}

# Celery Beat schedule examples:
# crontab(hour=0, minute=0) - Daily at midnight
# crontab(hour=0, minute=0, day_of_week=0) - Weekly on Monday at midnight
# crontab(0, 0, day_of_month='1') - Monthly on the 1st at midnight
# crontab(hour='*/6') - Every 6 hours
# timedelta(seconds=30) - Every 30 seconds
# timedelta(minutes=5) - Every 5 minutes
# timedelta(hours=1) - Every hour
# timedelta(days=1) - Every day
