import logging
from django.db.models.signals import post_save, post_delete
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.core.cache import cache
from users.tasks import send_welcome_email_task, send_team_notification_task

#this gets your custom model correctly
User = get_user_model()
# Initialize logger for signals and cache operations
logger = logging.getLogger('users.signals')# logging is recording events that happen during execution,incase of errors you can trace back
cache_logger = logging.getLogger('users.cache')


@receiver(post_save, sender=User)
def notify_user_registration(sender, instance, created, **kwargs):
    """
    Signal handler that triggers when a new user registers.
    This handler queues asynchronous tasks to:
    1. Send a welcome email to the new user
    2. Notify the team about the new registration
    
    These tasks are executed asynchronously via Celery to avoid blocking
    the HTTP response, providing a better user experience.
    """
    if created:  # Only trigger on user creation, not on updates
        # Queue the welcome email task asynchronously
        send_welcome_email_task.delay(instance.id)
        
        # Queue the team notification task asynchronously
        send_team_notification_task.delay(instance.id)
        
        logger.info(f"✓ Queued email tasks for new user: {instance.email}")




   