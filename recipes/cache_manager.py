"""
Cache Management Utilities for Recipe Search Scenarios
======================================================

This module provides utilities to work with Django's Redis cache for different
search scenarios. All data is stored in Redis DB 1.

Cache Storage Location:
    Redis: redis://127.0.0.1:6379/1
    
Configured Timeouts (from settings.CACHE_TIMEOUT):
    recipe_search: 1 hour (3600 seconds)
    recipe_detail: 2 hours (7200 seconds)
    random_recipe: 30 minutes (1800 seconds)
    spoonacular: 24 hours (86400 seconds)
"""

from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_CACHE_ALIAS
from django.conf import settings
import logging
import hashlib
from functools import wraps

logger = logging.getLogger('recipes.cache')


class RecipeCacheManager:
    """
    Manager class for handling all recipe-related caching operations.
    Provides methods for caching different types of searches and data.
    """
    
    # Cache key prefixes for different search types
    PREFIXES = {
        'search': 'recipe:search:',              # General recipe search: recipe:search:{hash}
        'detail': 'recipe:detail:',              # Recipe detail: recipe:detail:{recipe_id}
        'random': 'recipe:random:',              # Random recipes: recipe:random:{user_id}
        'ingredient': 'recipe:ingredient:',      # Ingredient search: recipe:ingredient:{ingredient}
        'category': 'recipe:category:',          # Category filter: recipe:category:{category_id}
        'user_collection': 'recipe:collection:', # User collections: recipe:collection:{user_id}
        'spoonacular': 'recipe:spoon:',          # Spoonacular API: recipe:spoon:{api_query}
        'trending': 'recipe:trending:',          # Trending recipes: recipe:trending:{timeframe}
    }
    
    @staticmethod
    def generate_search_key(query, filters=None):
        """
        Generate a cache key for a search query with optional filters.
        
        Args:
            query (str): Search query string
            filters (dict): Optional filters (cuisine, difficulty, time, etc.)
            
        Returns:
            str: Cache key (example: recipe:search:abc123def456)
            
        Example:
            key = RecipeCacheManager.generate_search_key(
                query='pasta',
                filters={'cuisine': 'italian', 'time': 30}
            )
        """
        # Combine query and filters into a hashable string
        key_string = f"{query}|{str(filters)}" if filters else query
        # Create a hash to avoid excessively long key names
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{RecipeCacheManager.PREFIXES['search']}{key_hash}"
    
    @staticmethod
    def cache_search_results(query, results, filters=None, timeout=None):
        """
        Cache search results in Redis.
        
        Args:
            query (str): Search query
            results (list): List of recipe results (serialized data)
            filters (dict): Optional filters applied to search
            timeout (int): Cache duration in seconds (defaults to recipe_search timeout)
            
        Example:
            results = Recipe.objects.filter(title__icontains='pasta').values()
            RecipeCacheManager.cache_search_results(
                'pasta',
                results,
                {'cuisine': 'italian'},
                timeout=3600
            )
        """
        if timeout is None:
            timeout = settings.CACHE_TIMEOUT.get('recipe_search', 3600)
        
        key = RecipeCacheManager.generate_search_key(query, filters)
        cache.set(key, results, timeout)
        logger.info(f"✓ Cached search results for '{query}' | Key: {key}")
        return key
    
    @staticmethod
    def get_search_results(query, filters=None):
        """
        Retrieve cached search results from Redis.
        
        Args:
            query (str): Search query
            filters (dict): Optional filters
            
        Returns:
            list or None: Cached results if found, None otherwise
            
        Example:
            cached = RecipeCacheManager.get_search_results('pasta', {'cuisine': 'italian'})
            if cached:
                return cached
            # Otherwise fetch from DB
        """
        key = RecipeCacheManager.generate_search_key(query, filters)
        results = cache.get(key)
        
        if results:
            logger.info(f"✓ Cache HIT for search '{query}' | Key: {key}")
        else:
            logger.info(f"✗ Cache MISS for search '{query}' | Key: {key}")
        
        return results
    
    @staticmethod
    def cache_recipe_detail(recipe_id, recipe_data, timeout=None):
        """
        Cache individual recipe detail data.
        
        Args:
            recipe_id (int): Recipe ID
            recipe_data (dict): Full recipe serialized data
            timeout (int): Cache duration in seconds
            
        Example:
            recipe_data = RecipeSerializer(recipe).data
            RecipeCacheManager.cache_recipe_detail(recipe.id, recipe_data)
        """
        if timeout is None:
            timeout = settings.CACHE_TIMEOUT.get('recipe_detail', 7200)
        
        key = f"{RecipeCacheManager.PREFIXES['detail']}{recipe_id}"
        cache.set(key, recipe_data, timeout)
        logger.info(f"✓ Cached recipe detail (ID: {recipe_id}) | Key: {key}")
        return key
    
    @staticmethod
    def get_recipe_detail(recipe_id):
        """
        Get cached recipe detail.
        
        Args:
            recipe_id (int): Recipe ID
            
        Returns:
            dict or None: Cached recipe data
            
        Example:
            recipe = RecipeCacheManager.get_recipe_detail(42)
            if not recipe:
                recipe = Recipe.objects.get(id=42)
        """
        key = f"{RecipeCacheManager.PREFIXES['detail']}{recipe_id}"
        return cache.get(key)
    
    @staticmethod
    def cache_ingredient_search(ingredient, results, timeout=None):
        """
        Cache recipes by ingredient search.
        
        Args:
            ingredient (str): Ingredient name
            results (list): Matching recipes
            timeout (int): Cache duration
            
        Example:
            RecipeCacheManager.cache_ingredient_search(
                'tomato',
                Recipe.objects.filter(ingredients__name__icontains='tomato').values()
            )
        """
        if timeout is None:
            timeout = settings.CACHE_TIMEOUT.get('recipe_search', 3600)
        
        key = f"{RecipeCacheManager.PREFIXES['ingredient']}{ingredient.lower()}"
        cache.set(key, results, timeout)
        logger.info(f"✓ Cached ingredient search for '{ingredient}' | Key: {key}")
        return key
    
    @staticmethod
    def get_ingredient_search(ingredient):
        """Get cached recipes by ingredient."""
        key = f"{RecipeCacheManager.PREFIXES['ingredient']}{ingredient.lower()}"
        return cache.get(key)
    
    @staticmethod
    def cache_by_category(category_id, results, timeout=None):
        """
        Cache recipes filtered by category.
        
        Args:
            category_id (int): Category ID
            results (list): Recipes in this category
            timeout (int): Cache duration
        """
        if timeout is None:
            timeout = settings.CACHE_TIMEOUT.get('recipe_search', 3600)
        
        key = f"{RecipeCacheManager.PREFIXES['category']}{category_id}"
        cache.set(key, results, timeout)
        logger.info(f"✓ Cached category (ID: {category_id}) | Key: {key}")
        return key
    
    @staticmethod
    def get_by_category(category_id):
        """Get cached recipes by category ID."""
        key = f"{RecipeCacheManager.PREFIXES['category']}{category_id}"
        return cache.get(key)
    
    @staticmethod
    def cache_trending_recipes(timeframe, results, timeout=None):
        """
        Cache trending recipes for a specific timeframe.
        
        Args:
            timeframe (str): 'daily', 'weekly', 'monthly'
            results (list): Trending recipes
            timeout (int): Cache duration
            
        Example:
            RecipeCacheManager.cache_trending_recipes('weekly', trending_list)
        """
        if timeout is None:
            timeout = settings.CACHE_TIMEOUT.get('recipe_search', 3600)
        
        key = f"{RecipeCacheManager.PREFIXES['trending']}{timeframe}"
        cache.set(key, results, timeout)
        logger.info(f"✓ Cached trending recipes ({timeframe}) | Key: {key}")
        return key
    
    @staticmethod
    def get_trending_recipes(timeframe):
        """Get cached trending recipes."""
        key = f"{RecipeCacheManager.PREFIXES['trending']}{timeframe}"
        return cache.get(key)
    
    @staticmethod
    def cache_user_collection(user_id, collection_data, timeout=None):
        """
        Cache user's recipe collection.
        
        Args:
            user_id (int): User ID
            collection_data (dict): Collection data
            timeout (int): Cache duration
        """
        if timeout is None:
            timeout = settings.CACHE_TIMEOUT.get('recipe_detail', 7200)
        
        key = f"{RecipeCacheManager.PREFIXES['user_collection']}{user_id}"
        cache.set(key, collection_data, timeout)
        logger.info(f"✓ Cached user collection (User ID: {user_id}) | Key: {key}")
        return key
    
    @staticmethod
    def get_user_collection(user_id):
        """Get cached user collection."""
        key = f"{RecipeCacheManager.PREFIXES['user_collection']}{user_id}"
        return cache.get(key)
    
    @staticmethod
    def invalidate_recipe_cache(recipe_id):
        """
        Invalidate cache for a specific recipe (called when recipe is updated).
        
        Args:
            recipe_id (int): Recipe ID to invalidate
            
        Example:
            # When a recipe is updated, call this to clear its cache
            RecipeCacheManager.invalidate_recipe_cache(recipe_id)
        """
        # Invalidate detail cache
        detail_key = f"{RecipeCacheManager.PREFIXES['detail']}{recipe_id}"
        cache.delete(detail_key)
        logger.info(f"✓ Invalidated recipe detail cache (ID: {recipe_id})")
    
    @staticmethod
    def invalidate_all_search_cache():
        """
        Invalidate all search caches (use sparingly - expensive operation).
        Called when major data changes occur.
        """
        cache.delete_many(cache.keys(f"{RecipeCacheManager.PREFIXES['search']}*"))
        logger.warning("✓ Invalidated ALL search caches")
    
    @staticmethod
    def invalidate_category_cache(category_id):
        """Invalidate cache for recipes in a specific category."""
        key = f"{RecipeCacheManager.PREFIXES['category']}{category_id}"
        cache.delete(key)
        logger.info(f"✓ Invalidated category cache (ID: {category_id})")
    
    @staticmethod
    def get_cache_stats():
        """
        Get cache statistics (requires Redis client).
        
        Returns:
            dict: Cache statistics like size, entries, etc.
        """
        try:
            redis_client = cache._cache
            info = redis_client.info()
            return {
                'db': info.get('db1', {}),
                'memory_used': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return None
    
    @staticmethod
    def clear_all_recipe_cache():
        """
        Clear ALL recipe-related cache (use with caution!).
        This flushes the entire Redis DB 1.
        """
        cache.clear()
        logger.warning("✓ Cleared ALL cache data from Redis DB 1")


def cache_search(timeout=None):
    """
    Decorator for caching search view results.
    
    Usage:
        @cache_search(timeout=3600)
        def get_recipes(request):
            query = request.query_params.get('q', '')
            # Function execution...
            return response
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            query = request.query_params.get('q', '')
            filters = {
                'cuisine': request.query_params.get('cuisine'),
                'difficulty': request.query_params.get('difficulty'),
            }
            
            if query:
                # Try to get from cache
                cached = RecipeCacheManager.get_search_results(query, filters)
                if cached:
                    logger.info(f"✓ Returning cached results for '{query}'")
                    return cached
            
            # If not cached, execute function
            response = func(self, request, *args, **kwargs)
            
            # Cache the results
            if query and response.data:
                RecipeCacheManager.cache_search_results(
                    query,
                    response.data,
                    filters,
                    timeout
                )
            
            return response
        return wrapper
    return decorator


def invalidate_on_save(model_type='recipe'):
    """
    Decorator to invalidate relevant cache when model is saved.
    
    Usage in signals:
        @invalidate_on_save(model_type='recipe')
        def recipe_saved(sender, instance, **kwargs):
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(sender, instance, **kwargs):
            func(sender, instance, **kwargs)
            
            if model_type == 'recipe':
                RecipeCacheManager.invalidate_recipe_cache(instance.id)
            elif model_type == 'category':
                RecipeCacheManager.invalidate_category_cache(instance.id)
            
            logger.info(f"Cache invalidated for {model_type} (ID: {instance.id})")
        return wrapper
    return decorator
