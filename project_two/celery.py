"""
Celery configuration for the project_two project.

This module sets up Celery as the task queue system, with Redis as the message broker
and result backend. It enables asynchronous task execution for email sending and
scheduled jobs using Celery Beat.

For development: Celery should be running in a separate terminal
$ celery -A project_two worker -l info

For Celery Beat (scheduled tasks):
$ celery -A project_two beat -l info

Or run both together:
$ celery -A project_two worker --beat -l info
"""
import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings

# Set default Django settings
# for production, you would set this in your environment variables(aws secret manager)
#  or use a different settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_two.settings.dev')

app = Celery('project_two')

# Load configuration from Django settings
# Ensure all config keys are prefixed with 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
# This finds all tasks.py modules in your installed apps
app.autodiscover_tasks()

# Optional: Celery logging configuration
@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery setup"""
    print(f'Request: {self.request!r}')