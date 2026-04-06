"""
Celery tasks for the users app.
Handles asynchronous email sending for user registration and notifications.
"""
import logging
from celery import shared_task
from django.contrib.auth import get_user_model
'''for production,you would use a real email backend(SMTP,SendGrid,Amazon SES, etc.) 
and configure it in your settings.(secret manager or environment variables)'''
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()
logger = logging.getLogger('users.tasks')


@shared_task(bind=True, max_retries=3)
def send_welcome_email_task(self, user_id):
    """
    Celery task to send a welcome email to a newly registered user.
    
    Args:
        user_id: The ID of the user to send the welcome email to
        
    Returns:
        str: Success message or error details
        
    Retries on failure up to 3 times with exponential backoff.
    """
    try:
        user = User.objects.get(id=user_id)
        
        subject = "Welcome to Our Recipes App!"
        message = f"""
Hello {user.name or user.email},

Welcome to our Recipes Community! 🎉

We're excited to have you on board. You can now:
- Browse and share recipes with our community
- Create your own recipe collections
- Follow other chefs and food enthusiasts
- Discover new cooking techniques and ingredients

If you have any questions, feel free to reach out to our support team.

Happy cooking!

Best regards,
The Recipes App Team
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        logger.info(f"✓ Welcome email sent successfully to {user.email}")
        return f"Welcome email sent to {user.email}"
        
    except User.DoesNotExist:
        logger.error(f"✗ User with ID {user_id} not found")
        return f"User with ID {user_id} not found"
        
    except Exception as exc:
        logger.error(f"✗ Failed to send welcome email to user {user_id}: {str(exc)}")
        # Retry with exponential backoff (5s, 25s, 125s for 3 retries)
        raise self.retry(exc=exc, countdown=5 ** self.request.retries)


@shared_task(bind=True, max_retries=3)
def send_team_notification_task(self, user_id):
    """
    Celery task to notify the team about a new user registration.
    
    Args:
        user_id: The ID of the newly registered user
        
    Returns:
        str: Success message or error details
        
    Retries on failure up to 3 times with exponential backoff.
    """
    try:
        user = User.objects.get(id=user_id)
        
        subject = f"New User Registration: {user.name or user.email}"
        message = f"""
A new user has registered on the Recipes App!

User Details:
- Email: {user.email}
- Name: {user.name or "Not provided"}
- Date Joined: {user.date_joined}
- Is Chef: {user.is_chef}

Please review the user profile in the admin panel if needed.

Admin Panel: {settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'Admin Dashboard'}
        """
        
        # Team email addresses - update with your actual team emails
        team_emails = [
            'maludev26@gmail.com',
        ]
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            team_emails,
            fail_silently=False,
        )
        
        logger.info(f"✓ Team notification sent for new user: {user.email}")
        return f"Team notification sent for user {user.email}"
        
    except User.DoesNotExist:
        logger.error(f"✗ User with ID {user_id} not found")
        return f"User with ID {user_id} not found"
        
    except Exception as exc:
        logger.error(f"✗ Failed to send team notification for user {user_id}: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=5 ** self.request.retries)


@shared_task
def send_bulk_email_task(user_ids, subject, message):
    """
    Celery task to send emails to multiple users in bulk.
    Useful for newsletters, announcements, etc.
    
    Args:
        user_ids: List of user IDs to send emails to
        subject: Email subject
        message: Email message content
        
    Returns:
        dict: Statistics about sent/failed emails
    """
    sent_count = 0
    failed_count = 0
    
    try:
        users = User.objects.filter(id__in=user_ids)
        
        for user in users:
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                sent_count += 1
                logger.info(f"✓ Bulk email sent to {user.email}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"✗ Failed to send bulk email to {user.email}: {str(e)}")
        
        result = {
            'sent': sent_count,
            'failed': failed_count,
            'total': len(users)
        }
        logger.info(f"Bulk email task completed: {result}")
        return result
        
    except Exception as exc:
        logger.error(f"✗ Bulk email task failed: {str(exc)}")
        return {
            'sent': sent_count,
            'failed': failed_count,
            'error': str(exc)
        }
