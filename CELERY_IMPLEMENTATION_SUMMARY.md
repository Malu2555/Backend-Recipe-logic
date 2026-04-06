"""
CELERY & CRON JOB SETUP - IMPLEMENTATION SUMMARY
================================================

This document summarizes the files created and modified for Celery integration
and scheduled cron jobs in the project_two Django application.


FILES CREATED
=============

1. users/tasks.py
   - send_welcome_email_task()      : Async task for welcome emails
   - send_team_notification_task()  : Async task for team notifications
   - send_bulk_email_task()         : Async task for bulk emails
   
   Features:
   - Automatic retry on failure (up to 3 times with exponential backoff)
   - Proper error logging and handling
   - Works seamlessly with Django ORM

2. recipes/tasks.py
   - cleanup_expired_cache_task()   : Removes old Spoonacular cache
   - generate_cache_stats_task()    : Generates cache statistics
   
   Features:
   - Scheduled to run via Celery Beat
   - Integrated with existing spoonacular_services module

3. project_two/celery.py (UPDATED)
   - Complete Celery app configuration
   - Auto-discovers tasks from all Django apps
   - Includes logging setup
   
4. project_two/celery_config.py
   - Centralized Beat schedule configuration
   - Defines all periodic/cron tasks
   - Easy to add new scheduled tasks

5. CELERY_SETUP_GUIDE.md
   - Comprehensive documentation
   - Installation instructions
   - Running Celery in development and production
   - Troubleshooting guide

6. CELERY_QUICK_REFERENCE.md
   - Quick command reference
   - Common Celery commands
   - Debugging and monitoring


FILES MODIFIED
==============

1. users/signals.py
   BEFORE: Synchronous email sending (blocks HTTP request)
   AFTER:  Queues async Celery tasks (non-blocking)
   
   Changes:
   - Removed: send_welcome_email(), notify_team_about_registration()
   - Added: Import of Celery tasks
   - Signal now calls: send_welcome_email_task.delay(user.id)
   - Signal now calls: send_team_notification_task.delay(user.id)

2. project_two/__init__.py
   - Uncommented Celery app import
   - Ensures Celery is initialized when Django starts

3. project_two/settings/base.py
   Added:
   - 'django_celery_beat' to INSTALLED_APPS
   - 'django_celery_results' to INSTALLED_APPS
   - CELERY_BROKER_URL configuration
   - CELERY_RESULT_BACKEND configuration
   - CELERY_BEAT_SCHEDULE import
   - Celery task routing configuration
   - Celery logging configuration
   - Task timeouts and execution settings


ARCHITECTURE OVERVIEW
=====================

User Registration Flow:
    1. New user registers → Django creates User instance
    2. post_save signal fires → users.signals.notify_user_registration()
    3. Signal queues tasks (non-blocking):
       - send_welcome_email_task.delay(user.id)
       - send_team_notification_task.delay(user.id)
    4. HTTP request completes immediately (user sees success)
    5. Celery worker picks up tasks from Redis queue
    6. Worker executes tasks and sends emails
    7. Results stored in Redis result backend

Scheduled Tasks (Cron Jobs):
    1. Celery Beat scheduler runs at configured times
    2. Triggers cleanup_expired_cache_task daily at 2:00 AM
    3. Triggers cache_statistics task daily at 1:00 AM
    4. Tasks execute in Celery worker
    5. Results logged and stored

Message Flow:
    
    Django App → Redis Queue (Broker)
                  ↓
              Celery Worker
                  ↓
              Execute Task
                  ↓
              Redis Result Backend
                  ↓
              Django App (reads result if needed)


QUEUE STRUCTURE
===============

Two separate Redis databases:
    - DB 2: Task Queue (CELERY_BROKER_URL) - stores pending tasks
    - DB 3: Result Backend (CELERY_RESULT_BACKEND) - stores task results

Task Routing (optional):
    - email queue: All users.tasks.* tasks
    - maintenance queue: All recipes.tasks.* tasks

This allows running separate workers for different task types if needed.


HOW TO USE
==========

1. SEND WELCOME EMAIL (Automatic on User Signup):
   
   When user signs up:
   - Signal automatically queues welcome email task
   - No code needed, happens automatically!
   
   Or manually in code:
   ```python
   from users.tasks import send_welcome_email_task
   send_welcome_email_task.delay(user_id)
   ```

2. SEND BULK EMAILS:
   
   ```python
   from users.tasks import send_bulk_email_task
   user_ids = [1, 2, 3, 4, 5]
   subject = "Newsletter: Check out new recipes!"
   message = "This is the message content..."
   send_bulk_email_task.delay(user_ids, subject, message)
   ```

3. RUN CACHE CLEANUP MANUALLY:
   
   ```python
   from recipes.tasks import cleanup_expired_cache_task
   result = cleanup_expired_cache_task.delay(days=30)
   print(result.get())  # Wait and get result
   ```

4. SCHEDULE A NEW TASK:
   
   Add to celery_config.py:
   ```python
   CELERY_BEAT_SCHEDULE = {
       'my-task': {
           'task': 'myapp.tasks.my_task',
           'schedule': crontab(hour=3, minute=0),  # 3 AM daily
           'kwargs': {'param': 'value'}
       },
   }
   ```


DEVELOPMENT SETUP STEPS
=======================

1. Install Celery packages:
   pip install celery redis django-celery-beat django-celery-results

2. Ensure Redis is running:
   redis-server
   # or: sudo systemctl start redis-server

3. Run migrations (for django_celery_beat):
   python manage.py migrate

4. Start Celery worker (in a new terminal):
   celery -A project_two worker -l info

5. Start Celery Beat (in another terminal):
   celery -A project_two beat -l info

6. Run Django server normally:
   python manage.py runserver

7. Test by creating a new user:
   - User registration endpoint
   - Check Celery worker terminal for task execution
   - Check email settings to see if email was queued


PRODUCTION DEPLOYMENT STEPS
============================

1. Update settings/prod.py:
   CELERY_BROKER_URL = os.environ['CELERY_BROKER_URL']
   CELERY_RESULT_BACKEND = os.environ['CELERY_RESULT_BACKEND']
   CELERY_TASK_ALWAYS_EAGER = False

2. Install Supervisor:
   sudo apt-get install supervisor

3. Create Supervisor config (see CELERY_SETUP_GUIDE.md)

4. Start services:
   sudo systemctl restart supervisor

5. Monitor with Flower:
   pip install flower
   flower -A project_two --port=5555


EXISTING INTEGRATION
===================

Cleanup Command:
The existing recipes/management/Commands/cleanup.py can now work two ways:

1. Via management command (synchronous):
   python manage.py cleanup

2. Via Celery task (asynchronous, scheduled):
   - Scheduled daily at 2:00 AM via Celery Beat
   - Or call directly: cleanup_expired_cache_task.delay()

Both use the same underlying function: clear_expired_spoonacular_cache()


KEY CONFIGURATION DETAILS
=========================

Task Serialization: JSON
- Tasks are serialized to JSON format
- Safe, language-agnostic format
- Good for all use cases

Result Expiry: 3600 seconds (1 hour)
- Results kept for 1 hour after task completes
- Prevents result backend from growing unbounded
- Can be extended if needed

Task Timeouts:
- Hard limit: 30 minutes (task forcefully stopped)
- Soft limit: 25 minutes (graceful stop, warning sent)
- Configure in settings/base.py

Retries:
- Email tasks retry up to 3 times on failure
- Exponential backoff: 5s, 25s, 125s delays
- Good for handling temporary failures (network issues, etc.)

Timezone: UTC
- All task scheduling uses UTC
- Make sure your server is in correct timezone
- Or customize in settings


MONITORING & DEBUGGING
======================

View Active Tasks:
    celery -A project_two inspect active

View Task Status:
    celery -A project_two inspect query_task <TASK_ID>

Real-time Monitoring:
    celery -A project_two events
    # or with Flower:
    flower -A project_two

Check Redis:
    redis-cli
    > KEYS "*"  # See all Redis keys
    > DBSIZE    # Database size

Tail Worker Logs:
    tail -f logs/app.log | grep celery

Test Task Synchronously (for debugging):
    # Temporarily add to settings:
    CELERY_TASK_ALWAYS_EAGER = True
    # Then run code using the task - it executes immediately


COMMON ISSUES & SOLUTIONS
=========================

Issue: Tasks not executing
Solution: Check Celery worker is running
          Check Redis connection (redis-cli ping)
          Check logs in logs/ folder

Issue: "Redis connection refused"
Solution: Start Redis: redis-server
          Or check Redis port in settings

Issue: "ImportError: No module named celery"
Solution: pip install celery

Issue: Beat not running scheduled tasks
Solution: Check Celery Beat is running in another terminal
          Check celery_config.py for schedule definition
          Check logs for errors

Issue: Email not sending
Solution: Check email settings in dev.py or prod.py
          Verify SMTP credentials
          Check logs for SMTP errors


NEXT STEPS
==========

1. Install required packages (if not already done)
2. Start Redis
3. Run migrations: python manage.py migrate
4. Start Celery worker
5. Start Celery Beat (for scheduled tasks)
6. Test by registering a new user
7. Check Celery worker terminal for task execution
8. Verify email is sent

For detailed information and troubleshooting, see:
- CELERY_SETUP_GUIDE.md (comprehensive guide)
- CELERY_QUICK_REFERENCE.md (command reference)
"""
