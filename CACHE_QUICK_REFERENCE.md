"""
CACHE QUICK REFERENCE GUIDE
===========================
"""

# ============================================================================
# WHERE IS THE CACHE DATA STORED?
# ============================================================================

CACHE_STORAGE = """
┌─────────────────────────────────────────────────────────────┐
│                   REDIS DATABASE 1                          │
│          redis://127.0.0.1:6379/1  (Your Cache)            │
├──────────────────┬──────────────────┬──────────────────────┤
│ Key              │ Data             │ Timeout              │
├──────────────────┼──────────────────┼──────────────────────┤
│ recipe:search:   │ Search results   │ 1 hour               │
│ abc123def456     │ (JSON)           │ (3600 seconds)       │
├──────────────────┼──────────────────┼──────────────────────┤
│ recipe:detail:42 │ Recipe data      │ 2 hours              │
│                  │ (JSON)           │ (7200 seconds)       │
├──────────────────┼──────────────────┼──────────────────────┤
│ recipe:          │ Ingredient       │ 1 hour               │
│ ingredient:      │ search results   │ (3600 seconds)       │
│ tomato           │ (JSON)           │                      │
├──────────────────┼──────────────────┼──────────────────────┤
│ recipe:category: │ Category         │ 1 hour               │
│ 5                │ recipes          │ (3600 seconds)       │
├──────────────────┼──────────────────┼──────────────────────┤
│ recipe:trending: │ Trending list    │ 1 hour               │
│ weekly           │ (JSON)           │ (3600 seconds)       │
└──────────────────┴──────────────────┴──────────────────────┘

YOUR REDIS LAYOUT:
  DB 0 → Channels (WebSocket)
  DB 1 → Django Cache ✓ YOUR DATA HERE
  DB 2 → Celery Tasks
  DB 3 → Celery Results
"""

# ============================================================================
# QUICK COMMANDS REFERENCE
# ============================================================================

COMMANDS = """
VIEW WHAT'S CACHED:
──────────────────
redis-cli                    # Start Redis CLI
> SELECT 1                   # Switch to cache DB (DB 1)
> KEYS "*"                   # List all cache keys
> GET recipe:detail:42       # View specific cached data
> DBSIZE                     # Total number of cache entries
> FLUSHDB                    # Clear ALL cache (careful!)
> TTL recipe:detail:42       # How many seconds until expiry
> TYPE recipe:search:abc123  # Data type (usually 'string')


DJANGO SHELL:
──────────────
python manage.py shell

>>> from django.core.cache import cache
>>> cache.keys('*')                    # All cache keys
>>> cache.get('recipe:detail:42')      # Get specific data
>>> cache.delete('recipe:detail:42')   # Delete specific entry
>>> cache.clear()                      # Clear all cache
>>> cache.ttl('recipe:detail:42')      # Time until expiry


USE CACHE MANAGER:
──────────────────
$ python manage.py shell

>>> from recipes.cache_manager import RecipeCacheManager
>>> RecipeCacheManager.get_search_results('pasta')
>>> RecipeCacheManager.cache_search_results('pasta', results)
>>> RecipeCacheManager.invalidate_recipe_cache(42)
>>> RecipeCacheManager.get_cache_stats()
"""

# ============================================================================
# CACHE KEY PATTERNS
# ============================================================================

KEY_PATTERNS = """
PREFIX PATTERNS:
────────────────

recipe:search:{hash}          → Search queries
                               Key: recipe:search:abc123def456
                               Time: 1 hour
                               
recipe:detail:{id}            → Single recipe
                               Key: recipe:detail:42
                               Time: 2 hours
                               
recipe:ingredient:{name}      → Ingredient searches
                               Key: recipe:ingredient:tomato
                               Time: 1 hour
                               
recipe:category:{id}          → Category filters
                               Key: recipe:category:5
                               Time: 1 hour
                               
recipe:collection:{user_id}   → User saved recipes
                               Key: recipe:collection:123
                               Time: 2 hours
                               
recipe:trending:{timeframe}   → Trending recipes
                               Key: recipe:trending:weekly
                               Time: 1 hour
                               
recipe:random:{user_id}       → Random recipes
                               Key: recipe:random:456
                               Time: 30 minutes
                               
recipe:spoon:{query}          → External API
                               Key: recipe:spoon:xyz789
                               Time: 24 hours
"""

# ============================================================================
# CODE SNIPPETS - COPY & PASTE
# ============================================================================

SNIPPET_1 = """
SNIPPET 1: Import Cache Manager
──────────────────────────────

Add to top of recipes/views.py:
    from recipes.cache_manager import RecipeCacheManager
"""

SNIPPET_2 = """
SNIPPET 2: Cache Search Results
────────────────────────────────

In your search view:
    
    def get(self, request):
        query = request.query_params.get('q', '')
        
        # Try cache first
        cached = RecipeCacheManager.get_search_results(query)
        if cached:
            return Response(cached)
        
        # Query database
        results = Recipe.objects.filter(title__icontains=query)
        data = RecipeSerializer(results, many=True).data
        
        # Cache results
        RecipeCacheManager.cache_search_results(query, data)
        
        return Response(data)
"""

SNIPPET_3 = """
SNIPPET 3: Cache Recipe Details
────────────────────────────────

For detail view:
    
    def get(self, request, recipe_id):
        # Try cache
        cached = RecipeCacheManager.get_recipe_detail(recipe_id)
        if cached:
            return Response(cached)
        
        # Get from DB
        recipe = Recipe.objects.get(id=recipe_id)
        data = RecipeSerializer(recipe).data
        
        # Cache it
        RecipeCacheManager.cache_recipe_detail(recipe_id, data)
        
        return Response(data)
"""

SNIPPET_4 = """
SNIPPET 4: Invalidate Cache on Update
──────────────────────────────────────

In recipes/signals.py:
    
    from django.db.models.signals import post_save
    from django.dispatch import receiver
    from recipes.cache_manager import RecipeCacheManager
    
    @receiver(post_save, sender=Recipe)
    def clear_recipe_cache(sender, instance, **kwargs):
        if not instance.created:  # Only on updates
            RecipeCacheManager.invalidate_recipe_cache(instance.id)
"""

# ============================================================================
# CACHE TIMEOUTS - CONFIGURABLE
# ============================================================================

TIMEOUTS = """
Current Timeouts (in settings/base.py):
CACHE_TIMEOUT = {
    'recipe_search': 3600,          # 1 hour
    'recipe_detail': 7200,          # 2 hours  
    'random_recipe': 1800,          # 30 minutes
    'spoonacular': 86400,           # 24 hours
}

HOW TO CHANGE:
──────────────
Edit settings/base.py:

    CACHE_TIMEOUT = {
        'recipe_search': 1800,      # Change to 30 minutes
        'recipe_detail': 3600,      # Change to 1 hour
        'random_recipe': 300,       # Change to 5 minutes
        'spoonacular': 172800,      # Change to 2 days
    }

TIMEOUT DURATIONS:
  60 seconds = 1 minute
  300 seconds = 5 minutes
  1800 seconds = 30 minutes
  3600 seconds = 1 hour
  7200 seconds = 2 hours
  86400 seconds = 1 day
  604800 seconds = 1 week
"""

# ============================================================================
# PERFORMANCE EXPECTATIONS
# ============================================================================

PERFORMANCE = """
TYPICAL SPEED COMPARISON:

Database Query (No Cache):
  First request: ~200-300ms
  Every request: ~200-300ms
  ❌ Slow for popular searches

With Cache:
  First request: ~200-300ms (queries DB, stores in Redis)
  Cached requests: ~2-5ms (reads from Redis)
  ✓ 50-100x FASTER for cached requests!

CACHE HIT RATE TARGET:
  Poor: < 50%  (most requests miss cache)
  Good: 70-80%
  Excellent: > 90%
  
Check your hit rate:
  $ tail -f logs/cache.log | grep "HIT\\|MISS"
"""

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

TROUBLESHOOTING = """
PROBLEM: Cache not working
→ Check Redis is running: redis-cli ping
→ Check settings: CACHES['default']['LOCATION']
→ Check imports: from recipes.cache_manager import...
→ Check logs: tail -f logs/cache.log

PROBLEM: Cache data seems stale
→ Check timeout is appropriate for your data
→ Implement cache invalidation on data changes
→ Clear cache manually: RecipeCacheManager.clear_all_recipe_cache()

PROBLEM: Memory usage too high
→ Reduce timeout durations
→ Clear unused cache entries
→ Monitor with: redis-cli SELECT 1; DBSIZE

PROBLEM: Cache key conflicts
→ Use unique prefixes for each search type (already done)
→ Include all filter params in cache key
→ Use hash for long search strings (already done)

PROBLEM: Inconsistent cached vs fresh data
→ Always invalidate cache when data changes
→ Use post_save signal to clear cache
→ Set appropriate timeout duration
"""

# ============================================================================
# SUMMARY TABLE
# ============================================================================

SUMMARY = """
┌────────────────────────────────────────────────────────────────┐
│                    CACHE SUMMARY TABLE                         │
├──────────────────┬─────────────┬──────────┬───────────────────┤
│ Scenario         │ Method      │ Timeout  │ When to Invalidate│
├──────────────────┼─────────────┼──────────┼───────────────────┤
│ Search Results   │ get_search_ │ 1 hour   │ Rarely needed     │
│                  │ results()   │          │ (data changes OK) │
├──────────────────┼─────────────┼──────────┼───────────────────┤
│ Recipe Details   │ get_recipe_ │ 2 hours  │ On recipe update  │
│                  │ detail()    │          │ (post_save signal)│
├──────────────────┼─────────────┼──────────┼───────────────────┤
│ Ingredient List  │ get_        │ 1 hour   │ On ingredient add │
│                  │ ingredient_ │          │                   │
│                  │ search()    │          │                   │
├──────────────────┼─────────────┼──────────┼───────────────────┤
│ Category Filter  │ get_by_     │ 1 hour   │ When recipes added│
│                  │ category()  │          │ to category       │
├──────────────────┼─────────────┼──────────┼───────────────────┤
│ User Collection  │ get_user_   │ 2 hours  │ On user update    │
│                  │ collection()│          │ collection        │
├──────────────────┼─────────────┼──────────┼───────────────────┤
│ Trending         │ get_        │ 1 hour   │ Automatically at  │
│ Recipes          │ trending_   │          │ timeout (daily)   │
│                  │ recipes()   │          │                   │
└──────────────────┴─────────────┴──────────┴───────────────────┘
"""

# ============================================================================
# MONITOR CACHE IN REAL-TIME
# ============================================================================

MONITORING = """
OPTION 1: Tail Cache Logs
──────────────────────────
$ tail -f logs/cache.log

Shows: ✓ Cache HIT for 'pasta' | Key: recipe:search:abc123
       ✓ Cache MISS for 'carbonara' | Key: recipe:search:def456
       ✓ Cached search results for 'pizza'


OPTION 2: Watch Redis DB Size
──────────────────────────────
$ watch 'redis-cli SELECT 1; redis-cli DBSIZE'

Updates every 2 seconds showing total cache entries


OPTION 3: Monitor Cache Operations
───────────────────────────────────
$ redis-cli MONITOR

Shows ALL Redis operations in real-time
(CPU intensive, use for debugging only)


OPTION 4: Track Performance
────────────────────────────
$ python manage.py shell
>>> import time
>>> start = time.time()
>>> data = cache.get('recipe:search:abc123')
>>> print(f"{(time.time() - start)*1000:.2f}ms")
0.87ms  ← Cache lookup speed
"""

print("""
╔════════════════════════════════════════════════════════════════╗
║           CACHE QUICK REFERENCE - START HERE                  ║
╚════════════════════════════════════════════════════════════════╝

WHERE IS CACHE STORED?
  → Redis Database 1 (redis://127.0.0.1:6379/1)

HOW TO VIEW CACHE?
  → redis-cli, then: SELECT 1; KEYS "*"

HOW TO USE IN CODE?
  → from recipes.cache_manager import RecipeCacheManager

BASIC PATTERN?
  → Check cache → Get from DB → Store in cache → Return

HOW TO IMPLEMENT?
  → See CACHE_IMPLEMENTATION_GUIDE.md (step by step)

HOW TO MONITOR?
  → tail -f logs/cache.log
  → Check for "HIT" vs "MISS" entries

EXPECTED SPEEDUP?
  → 50-100x faster for cached requests (200ms → 2ms)
""")
