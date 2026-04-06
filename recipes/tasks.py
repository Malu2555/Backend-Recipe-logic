"""
Celery tasks for the recipes app.
Handles scheduled maintenance tasks and automated cleanup jobs,i.e the cron job.
"""
import logging
from celery import shared_task
from recipes.api.spoonacular_services import clear_expired_spoonacular_cache

logger = logging.getLogger('recipes.tasks')


@shared_task
def cleanup_expired_cache_task(days=30):
    """
    Celery task to clean up expired Spoonacular API cache entries.
    
    This task removes old cached recipe data that is older than the specified
    number of days. Should be scheduled to run daily or weekly via Celery Beat.
    
    Args:
        days: Number of days to keep cache entries (default 30)
        
    Returns:
        dict: Information about the cleanup operation
    """
    try:
        count = clear_expired_spoonacular_cache(days=days)
        
        message = f'Successfully deleted {count} stale recipes from cache (older than {days} days).'
        logger.info(f"✓ Cache cleanup completed: {message}")
        
        return {
            'status': 'success',
            'deleted_count': count,
            'message': message
        }
        
    except Exception as exc:
        logger.error(f"✗ Cache cleanup task failed: {str(exc)}")
        return {
            'status': 'failed',
            'error': str(exc),
            'message': 'Failed to clean up expired cache entries'
        }


@shared_task
def generate_cache_stats_task():
    """
    Celery task to generate statistics about the Spoonacular cache.
    
    This task can be scheduled to monitor cache health and provide
    insights into cache usage patterns.
    
    Returns:
        dict: Cache statistics including size, entry count, etc.
    """
    try:
        from recipes.models import SpoonacularCache
        
        cache_stats = {
            'total_entries': SpoonacularCache.objects.count(),
            'oldest_entry': SpoonacularCache.objects.order_by('created_at').first(),
            'newest_entry': SpoonacularCache.objects.order_by('-created_at').first(),
        }
        
        logger.info(f"✓ Cache stats generated: {cache_stats['total_entries']} entries")
        return {
            'status': 'success',
            'total_entries': cache_stats['total_entries'],
            'message': f"Cache contains {cache_stats['total_entries']} entries"
        }
        
    except Exception as exc:
        logger.error(f"✗ Cache stats task failed: {str(exc)}")
        return {
            'status': 'failed',
            'error': str(exc),
            'message': 'Failed to generate cache statistics'
        }
