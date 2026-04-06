"""
Quick Reference for Celery Commands
====================================
"""

# ============================================================================
# RUNNING CELERY IN DEVELOPMENT
# ============================================================================

# Terminal 1: Start Redis (if needed)
redis-server

# Terminal 2: Start Celery Worker
celery -A project_two worker -l info

# Terminal 3: Start Celery Beat (for scheduled tasks)
celery -A project_two beat -l info

# Terminal 4: Run Django development server
python manage.py runserver


# ============================================================================
# CELERY WORKER COMMANDS
# ============================================================================

# Basic worker (processes all tasks)
celery -A project_two worker -l info

# Worker with autoscaling (min 3 workers, max 10)
celery -A project_two worker -l info --autoscale=10,3

# Worker for specific queues only
celery -A project_two worker -l info -Q email,maintenance

# Worker with concurrency limit
celery -A project_two worker -l info -c 4

# Worker with auto-reload on code changes
celery -A project_two worker -l info --autoreload

# Worker + Beat combined (development only - not recommended for production)
celery -A project_two worker --beat -l info


# ============================================================================
# CELERY BEAT COMMANDS
# ============================================================================

# Start Beat scheduler
celery -A project_two beat -l info

# Beat with persistent schedule (stores in Django database)
celery -A project_two beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler


# ============================================================================
# TASK INSPECTION & MONITORING
# ============================================================================

# See active tasks being processed
celery -A project_two inspect active

# See scheduled tasks
celery -A project_two inspect scheduled

# See reserved tasks (assigned but not yet running)
celery -A project_two inspect reserved

# See worker statistics
celery -A project_two inspect stats

# Query specific task by ID
celery -A project_two inspect query_task <TASK_ID>

# Real-time event monitoring
celery -A project_two events

# Web-based monitoring (requires: pip install flower)
flower -A project_two --port=5555


# ============================================================================
# TASK QUEUE MANAGEMENT
# ============================================================================

# Purge all queued tasks (WARNING: Deletes all tasks!)
celery -A project_two purge

# See queue depth
celery -A project_two inspect active_queues

# Get task details by ID (in Python shell)
python manage.py shell
>>> from celery.result import AsyncResult
>>> result = AsyncResult('<task_id>')
>>> result.status  # PENDING, STARTED, SUCCESS, FAILURE
>>> result.result  # Task result


# ============================================================================
# REDIS COMMANDS
# ============================================================================

# Check Redis connection
redis-cli ping

# View Redis database info
redis-cli INFO

# List all keys in Redis
redis-cli KEYS "*"

# Clear specific Redis database (Celery tasks are in DB 2)
redis-cli -n 2 FLUSHDB

# Clear all Redis databases (WARNING!)
redis-cli FLUSHALL

# Monitor Redis commands in real-time
redis-cli MONITOR

# Check Celery tasks in Redis
redis-cli -n 2 KEYS "*"


# ============================================================================
# DJANGO MANAGEMENT COMMANDS FOR CELERY
# ============================================================================

# Run a task directly (synchronous, for testing)
python manage.py shell
>>> from users.tasks import send_welcome_email_task
>>> user_id = 1
>>> send_welcome_email_task.delay(user_id)

# View Beat schedule (via Django admin)
python manage.py runserver
# Navigate to: http://localhost:8000/admin/django_celery_beat/


# ============================================================================
# DEBUGGING & TROUBLESHOOTING
# ============================================================================

# Test if Celery can connect to Redis
python -c "from celery import Celery; app = Celery(); app.broker_connection().connect()"

# Run task synchronously (good for debugging)
# Add to settings: CELERY_TASK_ALWAYS_EAGER = True
python manage.py shell
>>> from users.tasks import send_welcome_email_task
>>> result = send_welcome_email_task.delay(1)
>>> print(result.result)  # Immediate result

# Check task status
celery -A project_two inspect query_task <TASK_ID>

# View worker logs
celery -A project_two worker -l debug  # More verbose logging


# ============================================================================
# LOG LEVELS
# ============================================================================

# DEBUG - Most verbose, all messages
celery -A project_two worker -l debug

# INFO - General information, default for production
celery -A project_two worker -l info

# WARNING - Only warnings and errors
celery -A project_two worker -l warning

# ERROR - Only errors
celery -A project_two worker -l error


# ============================================================================
# COMMON DEVELOPMENT WORKFLOW
# ============================================================================

# To send a welcome email to user ID 5:
python manage.py shell
>>> from users.tasks import send_welcome_email_task
>>> send_welcome_email_task.delay(5)

# To verify it was queued:
# Check the worker terminal - you should see a message like:
# Received task: users.tasks.send_welcome_email_task[<task_id>]
# Task users.tasks.send_welcome_email_task[<task_id>] succeeded in 1.23s: 'Welcome email sent to user@example.com'


# ============================================================================
# PRODUCTION TIPS
# ============================================================================

# Use persistent result backend (PostgreSQL instead of Redis)
CELERY_RESULT_BACKEND = 'db+postgresql://user:password@localhost/celery_results'

# Use multiple workers with process manager (Supervisor, systemd)
# See CELERY_SETUP_GUIDE.md for Supervisor configuration

# Enable task result expiration to avoid database bloat
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour

# Monitor with external service (e.g., Sentry for error tracking)
import sentry_sdk
sentry_sdk.init("your-sentry-dsn")
