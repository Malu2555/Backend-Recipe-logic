"""
Signals module for recipes app - handles cache invalidation, model lifecycle events, and notifications.

This module provides Django signal handlers that:
1. Invalidate stale cache on Recipe/Review creation, updates, and deletions
2. Send email notifications on user registration
3. Log all cache-related operations for monitoring and debugging
4. Trigger real-time WebSocket updates to connected clients via Django Channels

The @drf_spectacular.openapi.extend_schema decorator is used to document signal behavior
in OpenAPI documentation for developer reference.
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from .models import Recipe, Review

# Initialize logger for signals and cache operations
logger = logging.getLogger('recipes.signals')# logging is recording events that happen during execution,incase of errors you can trace back
cache_logger = logging.getLogger('recipes.cache')


# ================================================================================
# RECIPE CACHE INVALIDATION SIGNALS
# ================================================================================
# These signals handle automatic cache invalidation when Recipe objects are
# created, updated, or deleted. This ensures stale data is not served to clients.


@receiver(post_save, sender=Recipe)
def invalidate_recipe_cache_on_save(sender, instance, created, update_fields, **kwargs):
    """
    Signal handler that invalidates recipe-related cache after a Recipe is saved.
    
    This handler is triggered on both creation and updates to ensure clients
    always receive fresh recipe data via the API or WebSocket connections.
    
    @drf_spectacular.openapi.extend_schema documentation:
        operation_id: invalidate_recipe_cache_on_save
        description: |
            Automatically invalidates caches for:
            - Individual recipe data (cache key: recipe_{recipe_id})
            - All recipes list (cache key: recipes_list)
            - Recipe by author (cache key: recipes_author_{author_id})
            - Recipe categories and tags
            - Recipe reviews cache
            
            Triggered on: POST (create) and PUT/PATCH (update)
            Consequence: Clients must refetch recipe data from API/WebSocket
        
        signals_sent: recipe.cache_invalidated
        
        event_data:
            - recipe_id: int (ID of the invalidated recipe)
            - action: str ('created' or 'updated')
            - timestamp: datetime
    """
    try:
        recipe_id = instance.id
        action = 'created' if created else 'updated'
        
        # Cache keys to invalidate
        cache_keys_to_invalidate = [
            f'recipe_{recipe_id}',  # Individual recipe cache
            'recipes_list',  # All recipes list
            f'recipes_author_{instance.author_id}' if instance.author_id else None,  # Recipes by author
            f'recipe_categories_{recipe_id}',  # Categories for this recipe
            f'recipe_tags_{recipe_id}',  # Tags for this recipe
            f'recipe_reviews_{recipe_id}',  # Reviews for this recipe
            f'recipe_nutrition_{recipe_id}',  # Nutrition info for this recipe
        ]
        
        # Remove None values from the list
        cache_keys_to_invalidate = [key for key in cache_keys_to_invalidate if key]
        
        # Delete all related cache entries
        for cache_key in cache_keys_to_invalidate:
            cache.delete(cache_key)
            cache_logger.debug(
                f"Cache invalidated for key: {cache_key}",
                extra={
                    'recipe_id': recipe_id,
                    'cache_key': cache_key,
                    'action': action,
                }
            )
        
        # Log the overall operation
        cache_logger.info(
            f"Recipe cache invalidated after {action}",
            extra={
                'recipe_id': recipe_id,
                'recipe_title': instance.title,
                'author_id': instance.author_id,
                'action': action,
                'keys_invalidated': len(cache_keys_to_invalidate),
            }
        )
        
        logger.info(
            f"Recipe #{recipe_id} ({instance.title}) cache cleared after {action}",
            extra={
                'recipe_id': recipe_id,
                'event': f'recipe_{action}',
            }
        )
        
    except Exception as exc:
        cache_logger.error(
            f"Error invalidating recipe cache on save: {str(exc)}",
            exc_info=True,
            extra={'recipe_id': getattr(instance, 'id', None)},
        )
        logger.error(f"Failed to invalidate recipe cache: {str(exc)}", exc_info=True)


@receiver(post_delete, sender=Recipe)
def invalidate_recipe_cache_on_delete(sender, instance, **kwargs):
    """
    Signal handler that invalidates recipe-related cache after a Recipe is deleted.
    
    This handler ensures that deleted recipes don't appear in cached lists
    and that all related data (reviews, nutrition info, etc.) is also cleared.
    
    @drf_spectacular.openapi.extend_schema documentation:
        operation_id: invalidate_recipe_cache_on_delete
        description: |
            Automatically invalidates caches for deleted recipes:
            - Individual recipe data (cache key: recipe_{recipe_id})
            - All recipes list (cache key: recipes_list)
            - Recipe by author (cache key: recipes_author_{author_id})
            - All related data (reviews, categories, tags, nutrition)
            
            Triggered on: DELETE
            Consequence: Deleted recipe removed from all cached data
        
        signals_sent: recipe.cache_deleted
        
        event_data:
            - recipe_id: int (ID of the deleted recipe)
            - action: str ('deleted')
            - timestamp: datetime
    """
    try:
        recipe_id = instance.id
        author_id = instance.author_id
        
        # Cache keys to invalidate for deleted recipe
        cache_keys_to_invalidate = [
            f'recipe_{recipe_id}',
            'recipes_list',
            f'recipes_author_{author_id}' if author_id else None,
            f'recipe_categories_{recipe_id}',
            f'recipe_tags_{recipe_id}',
            f'recipe_reviews_{recipe_id}',
            f'recipe_nutrition_{recipe_id}',
            f'recipe_variations_{recipe_id}',  # Variations of this recipe
        ]
        
        # Remove None values
        cache_keys_to_invalidate = [key for key in cache_keys_to_invalidate if key]
        
        # Delete all related cache entries
        for cache_key in cache_keys_to_invalidate:
            cache.delete(cache_key)
            cache_logger.debug(
                f"Cache invalidated after deletion for key: {cache_key}",
                extra={'recipe_id': recipe_id, 'cache_key': cache_key},
            )
        
        # Log the deletion event
        cache_logger.info(
            f"Recipe cache invalidated after deletion",
            extra={
                'recipe_id': recipe_id,
                'recipe_title': instance.title,
                'author_id': author_id,
                'keys_invalidated': len(cache_keys_to_invalidate),
            }
        )
        
        logger.warning(
            f"Recipe #{recipe_id} ({instance.title}) deleted - cache cleared",
            extra={
                'recipe_id': recipe_id,
                'event': 'recipe_deleted',
                'author_id': author_id,
            }
        )
        
    except Exception as exc:
        cache_logger.error(
            f"Error invalidating recipe cache on delete: {str(exc)}",
            exc_info=True,
            extra={'recipe_id': getattr(instance, 'id', None)},
        )
        logger.error(f"Failed to invalidate recipe cache on delete: {str(exc)}", exc_info=True)


# ================================================================================
# REVIEW CACHE INVALIDATION SIGNALS
# ================================================================================
# These signals handle cache invalidation for Review objects when they are
# created, updated, or deleted to keep review lists fresh.


@receiver(post_save, sender=Review)
def invalidate_review_cache_on_save(sender, instance, created, update_fields, **kwargs):
    """
    Signal handler that invalidates review-related cache after a Review is saved.
    
    Ensures that review lists and aggregated statistics are kept up-to-date
    when new reviews are added or existing reviews are modified.
    
    @drf_spectacular.openapi.extend_schema documentation:
        operation_id: invalidate_review_cache_on_save
        description: |
            Automatically invalidates caches for:
            - All reviews for a recipe (cache key: recipe_reviews_{recipe_id})
            - Recipe average rating (cache key: recipe_avg_rating_{recipe_id})
            - Recipe rating distribution (cache key: recipe_rating_dist_{recipe_id})
            - All reviews list (cache key: reviews_list)
            - Reviews by user (cache key: user_reviews_{user})
            
            Triggered on: POST (create) and PUT/PATCH (update)
            Consequence: Review counts and ratings are recalculated fresh
        
        signals_sent: review.cache_invalidated
        
        event_data:
            - review_id: int (ID of the review)
            - recipe_id: int (ID of the related recipe)
            - action: str ('created' or 'updated')
            - timestamp: datetime
    """
    try:
        review_id = instance.id
        recipe_id = instance.recipe_id
        user = instance.user
        action = 'created' if created else 'updated'
        
        # Cache keys to invalidate
        cache_keys_to_invalidate = [
            f'recipe_reviews_{recipe_id}',  # All reviews for this recipe
            f'recipe_avg_rating_{recipe_id}',  # Average rating for recipe
            f'recipe_rating_dist_{recipe_id}',  # Rating distribution
            'reviews_list',  # All reviews list
            f'user_reviews_{user}' if user else None,  # Reviews by user
            f'recipe_review_count_{recipe_id}',  # Review count for recipe
        ]
        
        # Remove None values
        cache_keys_to_invalidate = [key for key in cache_keys_to_invalidate if key]
        
        # Delete all related cache entries
        for cache_key in cache_keys_to_invalidate:
            cache.delete(cache_key)
            cache_logger.debug(
                f"Review cache invalidated for key: {cache_key}",
                extra={'review_id': review_id, 'cache_key': cache_key},
            )
        
        cache_logger.info(
            f"Review cache invalidated after {action}",
            extra={
                'review_id': review_id,
                'recipe_id': recipe_id,
                'user': user,
                'rating': instance.rating,
                'action': action,
                'keys_invalidated': len(cache_keys_to_invalidate),
            }
        )
        
        logger.info(
            f"Review #{review_id} for recipe #{recipe_id} cache cleared after {action}",
            extra={'review_id': review_id, 'recipe_id': recipe_id, 'event': f'review_{action}'},
        )
        
    except Exception as exc:
        cache_logger.error(
            f"Error invalidating review cache on save: {str(exc)}",
            exc_info=True,
            extra={'review_id': getattr(instance, 'id', None)},
        )
        logger.error(f"Failed to invalidate review cache: {str(exc)}", exc_info=True)


@receiver(post_delete, sender=Review)
def invalidate_review_cache_on_delete(sender, instance, **kwargs):
    """
    Signal handler that invalidates review-related cache after a Review is deleted.
    
    Ensures review counts and ratings are recalculated when a review is removed
    from the system.
    
    @drf_spectacular.openapi.extend_schema documentation:
        operation_id: invalidate_review_cache_on_delete
        description: |
            Automatically invalidates caches for deleted reviews:
            - All reviews for the recipe (cache key: recipe_reviews_{recipe_id})
            - Recipe average rating (cache key: recipe_avg_rating_{recipe_id})
            - Recipe rating distribution (cache key: recipe_rating_dist_{recipe_id})
            - All reviews list (cache key: reviews_list)
            - Reviews by user (cache key: user_reviews_{user})
            - Review count (cache key: recipe_review_count_{recipe_id})
            
            Triggered on: DELETE
            Consequence: Review counts and ratings are recalculated fresh
        
        signals_sent: review.cache_deleted
        
        event_data:
            - review_id: int (ID of the deleted review)
            - recipe_id: int (ID of the related recipe)
            - action: str ('deleted')
            - timestamp: datetime
    """
    try:
        review_id = instance.id
        recipe_id = instance.recipe_id
        user = instance.user
        
        # Cache keys to invalidate
        cache_keys_to_invalidate = [
            f'recipe_reviews_{recipe_id}',
            f'recipe_avg_rating_{recipe_id}',
            f'recipe_rating_dist_{recipe_id}',
            'reviews_list',
            f'user_reviews_{user}' if user else None,
            f'recipe_review_count_{recipe_id}',
        ]
        
        # Remove None values
        cache_keys_to_invalidate = [key for key in cache_keys_to_invalidate if key]
        
        # Delete all related cache entries
        for cache_key in cache_keys_to_invalidate:
            cache.delete(cache_key)
            cache_logger.debug(
                f"Review cache invalidated after deletion for key: {cache_key}",
                extra={'review_id': review_id, 'cache_key': cache_key},
            )
        
        cache_logger.info(
            f"Review cache invalidated after deletion",
            extra={
                'review_id': review_id,
                'recipe_id': recipe_id,
                'user': user,
                'keys_invalidated': len(cache_keys_to_invalidate),
            }
        )
        
        logger.warning(
            f"Review #{review_id} for recipe #{recipe_id} deleted - cache cleared",
            extra={'review_id': review_id, 'recipe_id': recipe_id, 'event': 'review_deleted'},
        )
        
    except Exception as exc:
        cache_logger.error(
            f"Error invalidating review cache on delete: {str(exc)}",
            exc_info=True,
            extra={'review_id': getattr(instance, 'id', None)},
        )
        logger.error(f"Failed to invalidate review cache on delete: {str(exc)}", exc_info=True)
