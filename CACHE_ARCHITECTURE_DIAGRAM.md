# Cache System Architecture & Data Flow

Complete system architecture showing recipe search caching, saved recipes management, Celery task queue, and email processing.

---

## Complete System Architecture

```
╔════════════════════════════════════════════════════════════════════════════╗
║                     COMPLETE BACKEND SYSTEM ARCHITECTURE                   ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT (Web/Mobile)                           │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐    │
│  │GET /api/recipes/ │  │POST /api/token/  │  │GET /api/saved-   │    │
│  │ (search)         │  │ (authenticate)   │  │ recipes/         │    │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘    │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐                          │
│  │POST /api/        │  │POST /api/register│                          │
│  │saved-recipes/    │  │ (create account) │                          │
│  └──────────────────┘  └──────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘
                              ↓↓↓
╔════════════════════════════════════════════════════════════════════════════╗
║                      DJANGO REST FRAMEWORK API                             ║
║  ────────────────────────────────────────────────────────────           ║
║                                                                            ║
║  Authentication: JWT Token (rest_framework_simplejwt)                    ║
║  Permission: IsAuthenticated required for most endpoints                 ║
║                                                                            ║
║  Routes:                                                                  ║
║  • POST   /api/token/                → TokenObtainPairView (login)      ║
║  • POST   /api/register/             → UserRegistrationView            ║
║  • GET    /api/recipes/?q=pasta      → RecipeViewSet (search + cache)  ║
║  • GET    /api/recipes/{id}/         → RecipeDetailView (detail cache) ║
║  • GET    /api/saved-recipes/        → LocalRecipeViewSet              ║
║  • POST   /api/saved-recipes/        → Create saved recipe             ║
║  • PUT    /api/saved-recipes/{id}/   → Update saved recipe             ║
║  • DELETE /api/saved-recipes/{id}/   → Delete saved recipe             ║
╚════════════════════════════════════════════════════════════════════════════╝
    │                   │                      │
    ├─→ [Cache Check]   ├─→ [Auth Check]     ├─→ [Permission]
    │   (Redis DB 1)    │   (JWT Token)      │   (IsAuthenticated)
    ↓                   ↓                     ↓
┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐
│ SEARCH RECIPES   │  │ AUTHENTICATE     │  │ SAVED RECIPES DB   │
│ ────────────────│  │ ────────────────│  │ ──────────────────│
│                  │  │                  │  │                    │
│ RecipeCache:     │  │ User.objects.    │  │ LocalRecipe Model: │
│ • Check Redis    │  │ get(id=user_id)  │  │ • owner (FK→User)  │
│ • Key pattern:   │  │                  │  │ • title            │
│   recipe:        │  │ Validate token   │  │ • instructions     │
│   search:hash    │  │ Verify signature │  │ • spoonacular_id   │
│ • TTL: 1-3 hours│  │ Extract user id  │  │ • created_at       │
└──────────────────┘  └──────────────────┘  └────────────────────┘
    │                      │
    ↓ CACHE MISS           ↓ NEW USER
┌──────────────────┐    ┌──────────────────────┐
│ FETCH FROM DB    │    │ TRIGGER CELERY TASK  │
│ ────────────────│    │ ──────────────────── │
│                  │    │                      │
│ Spoonacular API: │    │ Django Signal:       │
│ • Search recipes │    │ post_save(User)      │
│ • Get details    │    │                      │
│ • Rate limited   │    │ Queue tasks to DB 2: │
│ • Locally cached │    │ • send_welcome_email │
│ • Time: 300ms-1s│    │ • send_team_notif    │
└──────────────────┘    └──────────────────────┘
    │                           │
    ↓ SERIALIZE & CACHE          ↓
┌──────────────────────────────────┐  ┌────────────────────────┐
│ RecipeSerializer                 │  │ CELERY WORKER PROCESS  │
│ ────────────────────────────────│  │ ──────────────────────│
│                                  │  │ $ celery -A project.. │
│ Store in Redis DB 1:             │  │ worker -l info        │
│ recipe:search:abc123def456       │  │                       │
│ Expires: 3600s (1 hour)          │  │ Fetch user from DB    │
│ Speed: ~1-2ms to store           │  │ Prepare email content │
└──────────────────────────────────┘  │ Retry 3x max          │
    │                                  │ Exponential backoff   │
    │                                  └────────────────────────┘
    │                                          │
    │                                  ┌────────────────────┐
    │                                  │ EMAIL BACKEND      │
    │                                  │ ────────────────── │
    │                                  │                    │
    │                  ┌───────────────┼──────────────────┐ │
    │                  │               │                  │ │
    │                  ↓               ↓                  ↓ │
    │        DEVELOPMENT      →   PRODUCTION             │
    │        ─────────────            ─────────          │
    │        • Backend:          • Backend:              │
    │          console           sendgrid_backend      │
    │        • Output:           • API Key: secret     │
    │          terminal            manager             │
    │        • Speed:            • Speed: ~100-       │
    │          instant             200ms via API       │
    │        • Config:           • Config:            │
    │          dev.py             prod.py             │
    │                                                 │
    └─────────────────────────────────────────────────┘
                            ↓
    ┌────────────────────────────────────────────┐
    │ SEND EMAIL & STORE RESULT                  │
    │ ────────────────────────────────────      │
    │                                            │
    │ ✓ Email sent successfully                 │
    │ ✓ Task result in Redis DB 3               │
    │ ✓ Status: SUCCESS                         │
    │ ✓ TTL: 24 hours                           │
    └────────────────────────────────────────────┘
            │
            └─────────────────────────────┐
                                          ↓
    ┌────────────────────────────────────────────────────────────┐
    │  RESPONSE TO CLIENT                                        │
    │  ──────────────────────────────────────────────────────── │
    │  {                                                         │
    │    "count": 42,                                            │
    │    "results": [recipe1, recipe2, ...],                    │
    │    "from_cache": true/false                               │
    │  }                                                         │
    │                                                            │
    │  Total response time:                                      │
    │  • Cache hit: ~3-5ms                                       │
    │  • Cache miss: ~300-350ms                                 │
    └────────────────────────────────────────────────────────────┘
```

---

## Redis Database Layout

```
REDIS SERVER
├── localhost:6379 (development)
└── redis://host:6379 (production)

Database Segregation:
│
├── DB 0
│   └─ Django Channels (WebSocket real-time)
│      └─ Keys: channel_layers, group_messages
│
├── DB 1 (RECIPE CACHE)
│   ├─ recipe:search:8ee1b5f9b9f1e4f5...  (1 hour TTL)
│   ├─ recipe:detail:42                   (2 hour TTL)
│   ├─ recipe:detail:101                  (2 hour TTL)
│   ├─ recipe:ingredient:tomato           (1 hour TTL)
│   ├─ recipe:ingredient:pasta            (1 hour TTL)
│   ├─ recipe:category:5                  (1 hour TTL)
│   ├─ recipe:category:12                 (1 hour TTL)
│   ├─ recipe:trending:weekly             (1 hour TTL)
│   ├─ recipe:trending:monthly            (1 hour TTL)
│   └─ recipe:random:xyz123               (30 min TTL)
│
├── DB 2 (CELERY TASK QUEUE)
│   ├─ Task: send_welcome_email_task(user_id=5)
│   ├─ Task: send_team_notification_task(user_id=5)
│   ├─ Task: send_bulk_email_task(users=[1,2,3])
│   ├─ Task: cleanup_expired_cache_task()      [scheduled: 2 AM daily]
│   └─ Task: generate_cache_stats_task()       [scheduled: 1 AM daily]
│
└── DB 3 (CELERY TASK RESULTS)
    ├─ celery-task-id-abc → {status: SUCCESS, duration: 150ms}
    ├─ celery-task-id-def → {status: FAILURE, error: "..."}
    └─ celery-task-id-ghi → {status: PENDING, ...}
```

---

## Cache Hit Scenario (Timeline)

```
User searches: GET /api/recipes/?q=pasta&cuisine=italian

FIRST REQUEST (T = 0ms) - CACHE MISS
─────────────────────────────────────
T+0ms     → Check Redis DB 1 for key "recipe:search:abc123def456"
T+1ms     ↓ Not found (CACHE MISS)
T+2ms     → Query Spoonacular API / PostgreSQL database
T+250ms   ↓ Receive 42 matching recipes
T+251ms   → Serialize with RecipeSerializer
T+300ms   ↓ Convert to JSON format
T+302ms   → Store in Redis DB 1 (1 hour TTL)
T+303ms   → Return JSON response to client

TOTAL TIME: ~303ms  [1 API/DB hit + 1 cache write]
═══════════════════════════════════════════════════════════════


SUBSEQUENT REQUESTS (T = +5s, +1m, +30m) - CACHE HIT
──────────────────────────────────────────────────────
T+new     → Check Redis DB 1 for key "recipe:search:abc123def456"
T+2ms     ↓ FOUND! ✓ (CACHE HIT)
T+3ms     → Return cached JSON to client

TOTAL TIME: ~3ms   [0 API/DB hits, pure cache]

IMPROVEMENT: 303ms → 3ms = 100x faster! 🚀

For every additional identical request within 1 hour:
• Real database: ~300ms × 100 requests = 30 seconds
• With cache:    ~3ms × 100 requests = 0.3 seconds
• Savings: 29.7 seconds per 100 requests!
```

---

## User Registration Flow (with Email)

```
User Signup: POST /api/register/
{
  "email": "john@example.com",
  "password": "secure_password",
  "name": "John Doe"
}

T+0ms      → Validate email/password
T+10ms     → Create user in PostgreSQL
T+50ms     ↓ Django Signal: post_save(User)
T+51ms     → Queue Celery tasks:
           │  1. send_welcome_email_task(user_id=5)
           │  2. send_team_notification_task(user_id=5)
T+55ms     → Tasks stored in Redis DB 2 (queue)

T+60ms     ↓ RETURN RESPONSE TO CLIENT ✓
           {
             "id": 5,
             "email": "john@example.com",
             "name": "John Doe",
             "is_active": true
           }
           Total response time: ~60ms (FAST!)


PARALLEL PROCESSING (Celery Worker)
───────────────────────────────────
While client receives response, separately:

T+0ms      → Celery worker picks up task from Redis DB 2
T+5ms      → Fetch User(id=5) from PostgreSQL
T+20ms     → Prepare welcome email:
           Subject: "Welcome to Our Recipes App!"
           Body: [personalized message]
T+50ms     → Send via EMAIL_BACKEND:
           ├─ Development: outputs to console
           ├─ Production: sends via SendGrid API (~150ms)
T+200ms    → Task complete, store result in Redis DB 3
           {
             "task_id": "abc123xyz789",
             "status": "SUCCESS",
             "duration": "150ms"
           }

USER NEVER WAITS for email to send! ✓
Email sends in background while they use the app.
```

---

## Saved Recipes Flow (No Cache)

```
User saves recipe: POST /api/saved-recipes/
{
  "title": "Pasta Carbonara",
  "instructions": "Cook pasta. Fry bacon. Mix...",
  "spoonacular_id": 12345
}

T+0ms      → Extract JWT token from Authorization header
T+2ms      → Verify token signature & expiration
T+5ms      → Extract user_id from token claims
T+10ms     ↓ Check IsAuthenticated permission
T+12ms     → Validate serializer data:
           • title: required, max 255 chars
           • instructions: required
           • spoonacular_id: required, unique
T+25ms     → Create LocalRecipe:
           INSERT INTO recipes_localrecipe
           (owner_id, title, instructions, spoonacular_id, created_at)
           VALUES (5, 'Pasta...', 'Cook...', 12345, now())
T+75ms     → Serialize response:
           {
             "id": 1,
             "title": "Pasta Carbonara",
             "instructions": "Cook...",
             "spoonacular_id": 12345,
             "owner": 5,
             "owner_username": "john_doe"
           }
T+100ms    → Return response to client ✓

TOTAL TIME: ~100ms
DATA PERSISTED: Yes (survives app restart)
CACHED: No (always fresh from DB)


Get User's Saved Recipes: GET /api/saved-recipes/

T+0ms      → Authenticate (verify JWT token)
T+10ms     → Check permission (IsAuthenticated)
T+15ms     → Query:
           SELECT * FROM recipes_localrecipe
           WHERE owner_id = 5
           ORDER BY -id
T+40ms     → Serialize all recipes
T+50ms     ↓ Return JSON array to client ✓
           [
             {recipe1},
             {recipe2},
             {recipe3}
           ]

TOTAL TIME: ~50ms (depends on recipe count)
USER-SCOPED: Yes (filter by owner=request.user)
CACHED: No (direct DB query each time)
```

---

## Cache Invalidation & Updates

```
Recipe cached in Redis DB 1:
    recipe:detail:42 → {recipe data} ← 2 hours remaining (until expiry)

USER ACTION: Update recipe title
────────────────────────────────
    PATCH /api/recipes/42/
    {"title": "New Title"}

T+0ms      → Validate new data
T+20ms     → Update PostgreSQL:
           UPDATE recipes_recipe
           SET title = 'New Title'
           WHERE id = 42
T+40ms     ↓ Django Signal: post_save(Recipe)
T+41ms     → Call: invalidate_recipe_cache(recipe_id=42)
T+42ms     → Redis: DELETE recipe:detail:42
T+45ms     → Return updated data to client ✓

NEXT REQUEST: User views recipe 42
──────────────────────────────────
    GET /api/recipes/42/

T+0ms      → Check Redis for recipe:detail:42
T+2ms      ↓ NOT FOUND (was deleted by invalidation)
T+3ms      → Query PostgreSQL for fresh data
T+50ms     → Serialize new data
T+100ms    ↓ Store in Redis again (2 hour TTL)
T+105ms    → Return fresh recipe to client ✓

RESULT: User sees updated content immediately!
```

---

## Celery Task Queue

```
TASK TYPES:
═══════════

1. WELCOME EMAIL
   send_welcome_email_task(user_id)
   ├─ Trigger: User registration (post_save signal)
   ├─ Retry: 3 times max
   ├─ Backoff: 5s → 25s → 125s (exponential)
   ├─ Timeout: 5 minutes
   └─ Result stored: 24 hours in Redis DB 3

2. TEAM NOTIFICATION
   send_team_notification_task(user_id)
   ├─ Trigger: User registration (post_save signal)
   ├─ Recipients: Admin email
   ├─ Purpose: Alert staff of new user
   └─ Result stored: 24 hours in Redis DB 3

3. BULK EMAIL
   send_bulk_email_task(user_ids, subject, message)
   ├─ Trigger: Admin sends newsletter
   ├─ Scalable: Send to thousands of users
   ├─ Non-blocking: Admin doesn't wait
   └─ Result stored: 24 hours in Redis DB 3

4. CACHE CLEANUP (Scheduled)
   cleanup_expired_cache_task(days=30)
   ├─ Schedule: Daily at 2:00 AM UTC
   ├─ Purpose: Remove stale cache entries
   ├─ Configured in: settings/base.py
   ├─ Runner: celery -A project_two beat
   └─ Removes recipes not accessed in 30 days

5. CACHE STATISTICS (Scheduled)
   generate_cache_stats_task()
   ├─ Schedule: Daily at 1:00 AM UTC
   ├─ Purpose: Monitor cache health
   ├─ Configured in: settings/base.py
   ├─ Runner: celery -A project_two beat
   └─ Logs: cache statistics to file


RUNNING CELERY IN DEVELOPMENT:
════════════════════════════════

Terminal 1 (Worker):
$ celery -A project_two worker -l info
├─ Processes tasks from Redis DB 2
├─ Executes send_welcome_email_task, etc.
└─ Output: logs to terminal

Terminal 2 (Beat Scheduler):
$ celery -A project_two beat -l info
├─ Runs scheduled tasks at specified times
├─ Triggers cleanup_expired_cache_task
└─ Output: logs to terminal

OR Combined:
$ celery -A project_two worker --beat -l info
├─ Single terminal with both worker + beat
└─ Good for development


RUNNING CELERY IN PRODUCTION:
════════════════════════════════

Systemd service: /etc/systemd/system/celery.service
├─ Restart on failure
├─ Runs as www-data user
└─ Logs to /var/log/celery/worker.log

Docker container:
├─ CMD: celery -A project_two worker --loglevel=info
├─ Separate from web container
└─ Restart policy: always

Supervisor:
├─ Program: celery
├─ Autostart: true
└─ Autorestart: true
```

---

## Cache Manager Methods

```
recipes/cache_manager.py
│
└─ class RecipeCacheManager
   │
   ├─ SEARCH OPERATIONS
   │  ├─ get_search_results(query, filters)
   │  │   └─ Retrieve cached search results
   │  │
   │  └─ cache_search_results(query, results, filters)
   │      └─ Store search results in Redis (1hr TTL)
   │
   ├─ DETAIL OPERATIONS
   │  ├─ get_recipe_detail(recipe_id)
   │  │   └─ Retrieve cached recipe detail
   │  │
   │  └─ cache_recipe_detail(recipe_id, data)
   │      └─ Store recipe detail in Redis (2hr TTL)
   │
   ├─ INGREDIENT OPERATIONS
   │  ├─ get_ingredient_search(ingredient)
   │  │   └─ Get recipes containing ingredient
   │  │
   │  └─ cache_ingredient_search(ingredient, results)
   │      └─ Store ingredient search results (1hr TTL)
   │
   ├─ CATEGORY OPERATIONS
   │  ├─ get_by_category(category_id)
   │  │   └─ Get recipes in category
   │  │
   │  └─ cache_by_category(category_id, results)
   │      └─ Store category results (1hr TTL)
   │
   ├─ TRENDING OPERATIONS
   │  ├─ get_trending_recipes(timeframe)
   │  │   └─ Get trending recipes (weekly/monthly)
   │  │
   │  └─ cache_trending_recipes(timeframe, results)
   │      └─ Store trending results (1hr TTL)
   │
   ├─ INVALIDATION OPERATIONS
   │  ├─ invalidate_recipe_cache(recipe_id)
   │  │   └─ Clear specific recipe cache
   │  │
   │  ├─ invalidate_category_cache(category_id)
   │  │   └─ Clear category cache
   │  │
   │  ├─ invalidate_all_search_cache()
   │  │   └─ Clear all search caches
   │  │
   │  └─ clear_all_recipe_cache()
   │      └─ Clear entire cache (CAREFUL!)
   │
   └─ STATISTICS OPERATIONS
      └─ get_cache_stats()
          └─ Return cache health metrics


CACHE TIMEOUT CONFIGURATION (settings/base.py):
═════════════════════════════════════════════════

CACHE_TIMEOUT = {
    'search': 3600,         # 1 hour
    'detail': 7200,         # 2 hours
    'ingredient': 3600,     # 1 hour
    'category': 3600,       # 1 hour
    'trending': 3600,       # 1 hour
    'random': 1800,         # 30 minutes
    'spoonacular': 86400,   # 24 hours
}
```

---

## Key Metrics & Performance

```
SEARCH PERFORMANCE:
────────────────────
Without Cache:
    • Cold start: ~300-500ms
    • Database query: ~200-300ms
    • Serialization: ~50-100ms
    • Response: ~300-500ms total

With Cache (hit):
    • Redis lookup: ~1-2ms
    • Response: ~2-5ms total
    • IMPROVEMENT: 50-250x faster!

SAVED RECIPES PERFORMANCE:
──────────────────────────
CREATE (POST):
    • Validation: ~15ms
    • DB insert: ~30-50ms
    • Serialization: ~10-20ms
    • Response: ~100-150ms total

READ (GET):
    • Query 50 recipes: ~40-60ms
    • Serialization: ~20-30ms
    • Response: ~50-100ms total

UPDATE (PATCH):
    • Validation: ~15ms
    • DB update: ~20-30ms
    • Response: ~100-150ms total

DELETE:
    • DB delete: ~10-20ms
    • Response: ~50-100ms total

EMAIL TASK PERFORMANCE:
───────────────────────
End-to-end (user perspective):
    • Queued: 0-10ms
    • Response sent: ~60-100ms
    • User doesn't wait!

Worker processing (background):
    • Task pickup: ~1-5ms
    • Email composition: ~20-50ms
    • Send via API: ~100-200ms
    • Store result: ~5-10ms
    • Total: ~150-300ms

CONCURRENCY:
• Celery workers: configurable (default=4)
• Email throughput: ~20-50 emails/second
• Task queue depth: scales with Redis memory
```
                                    ↓
╔════════════════════════════════════════════════════════════════════════════╗
║ STEP 1: CHECK CACHE (REDIS DB 1)                                         ║
║ ────────────────────────────────                                         ║
║  from recipes.cache_manager import RecipeCacheManager                    ║
║  cached = RecipeCacheManager.get_search_results('pasta')                 ║
║                                                                            ║
║  Query Redis with key: recipe:search:8ee1b5f9b9f1e4f5e4f4e4f4e4f4e4f4   ║
╚════════════════════════════════════════════════════════════════════════════╝
                                    ↓
                        ┌───────────┴───────────┐
                        │                       │
                  ✓ CACHE HIT             ✗ CACHE MISS
                  (Found in Redis)       (Not in Redis)
                        │                       │
                        ↓                       ↓
                  Return Data         ┌─────────────────────┐
                  from Cache          │  STEP 2: HIT DB     │
                  ~2-5ms              │  ─────────────────  │
                  ✓ FAST!             │                     │
                        │             │ Recipe.objects.     │
                        │             │ filter(title...)    │
                        │             │                     │
                        │             │ Query Time:         │
                        │             │ ~200-300ms          │
                        │             │ ✗ SLOWER            │
                        │             └─────────────────────┘
                        │                     ↓
                        │             ┌──────────────────────┐
                        │             │  STEP 3: SERIALIZE   │
                        │             │  ──────────────────  │
                        │             │                      │
                        │             │ RecipeSerializer()   │
                        │             │ Convert to JSON      │
                        │             │ ~50-100ms            │
                        │             └──────────────────────┘
                        │                     ↓
                        │             ┌──────────────────────┐
                        │             │  STEP 4: CACHE      │
                        │             │  ─────────────────  │
                        │             │                      │
                        │             │ Store in Redis DB 1: │
                        │             │ Key: recipe:search:  │
                        │             │      {hash}          │
                        │             │ Timeout: 1 hour      │
                        │             │ Speed: ~1-2ms        │
                        │             └──────────────────────┘
                        │                     ↓
                        └────────────────┬────┘
                                        ↓
                    ┌────────────────────────────────────┐
                    │  RETURN RESPONSE TO CLIENT         │
                    │  ────────────────────────────      │
                    │  {                                  │
                    │    "count": 42,                     │
                    │    "results": [recipe data...],     │
                    │    "from_cache": true/false         │
                    │  }                                  │
                    └────────────────────────────────────┘
                                    ↓
                    ┌────────────────────────────────────┐
                    │        NEXT REQUEST SAME QUERY     │
                    │  GET /api/recipes/?q=pasta         │
                    │                                    │
                    │   → Finds in cache immediately!    │
                    │   → Returns in ~2-5ms              │
                    │   → 40-100x FASTER! 🚀             │
                    └────────────────────────────────────┘


════════════════════════════════════════════════════════════════════════════
REDIS DATABASE LAYOUT:
════════════════════════════════════════════════════════════════════════════

        REDIS SERVER (localhost:6379)
        │
        ├── DB 0 (indexes=0)
        │   └─ Channels (WebSocket real-time updates)
        │
        ├── DB 1 (indexes=1)  ← YOUR CACHE DATA HERE
        │   ├─ recipe:search:abc123
        │   │   ├─ Key: recipe:search:abc123def456
        │   │   ├─ Value: [serialized recipe data...]
        │   │   └─ Expires: 3600 seconds (1 hour)
        │   │
        │   ├─ recipe:detail:42
        │   │   ├─ Key: recipe:detail:42
        │   │   ├─ Value: {full recipe JSON}
        │   │   └─ Expires: 7200 seconds (2 hours)
        │   │
        │   ├─ recipe:ingredient:tomato
        │   │   ├─ Key: recipe:ingredient:tomato
        │   │   ├─ Value: [recipes with tomato...]
        │   │   └─ Expires: 3600 seconds (1 hour)
        │   │
        │   ├─ recipe:category:5
        │   │   ├─ Key: recipe:category:5
        │   │   ├─ Value: [recipes in category...]
        │   │   └─ Expires: 3600 seconds (1 hour)
        │   │
        │   └─ recipe:trending:weekly
        │       ├─ Key: recipe:trending:weekly
        │       ├─ Value: [top recipes...]
        │       └─ Expires: 3600 seconds (1 hour)
        │
        ├── DB 2 (indexes=2)
        │   └─ Celery Task Queue (email tasks, etc.)
        │
        └── DB 3 (indexes=3)
            └─ Celery Results (task execution results)


════════════════════════════════════════════════════════════════════════════
MULTIPLE REQUESTS - CACHE EFFECTIVENESS:
════════════════════════════════════════════════════════════════════════════

Timeline of 10 identical search requests:

Request  Time    Source         Speed        Database Hit?
────────────────────────────────────────────────────────────
  1     T+0ms   → DB Query     ~250ms       ✓ YES (miss cache)
  2     T+1s    ← Cache        ~5ms         ✗ NO (hit cache)
  3     T+2s    ← Cache        ~5ms         ✗ NO (hit cache)
  4     T+3s    ← Cache        ~5ms         ✗ NO (hit cache)
  5     T+4s    ← Cache        ~5ms         ✗ NO (hit cache)
  6     T+5s    ← Cache        ~5ms         ✗ NO (hit cache)
  7     T+6s    ← Cache        ~5ms         ✗ NO (hit cache)
  8     T+7s    ← Cache        ~5ms         ✗ NO (hit cache)
  9     T+8s    ← Cache        ~5ms         ✗ NO (hit cache)
  10    T+9s    ← Cache        ~5ms         ✗ NO (hit cache)

Total without cache: 10 × 250ms = 2,500ms ❌ SLOW
Total with cache:    1 × 250ms + 9 × 5ms = 295ms ✓ FAST
IMPROVEMENT: 2,500 / 295 = 8.5x faster! 🚀


════════════════════════════════════════════════════════════════════════════
CACHE INVALIDATION FLOW:
════════════════════════════════════════════════════════════════════════════

Recipe Exists in Cache:
    recipe:detail:42 → {recipe data} ← Time: 2 hours (until expiry)

User Updates Recipe:
    POST /api/recipes/42/update/
           ↓
    Django Signal: post_save (Recipe model)
           ↓
    Call: invalidate_recipe_cache(recipe_id=42)
           ↓
    Redis: DELETE recipe:detail:42
           ↓
    Next request for recipe 42:
           ↓
    Cache MISS (was deleted)
           ↓
    Query database → Get fresh data
           ↓
    Store in cache again
           ↓
    User sees updated recipe ✓


════════════════════════════════════════════════════════════════════════════
CACHE MANAGER CLASS STRUCTURE:
════════════════════════════════════════════════════════════════════════════

recipes/cache_manager.py
│
└─ class RecipeCacheManager
   │
   ├─ get_search_results(query, filters)
   │   └─ Retrieve cached search results
   │
   ├─ cache_search_results(query, results, filters)
   │   └─ Store search results in Redis
   │
   ├─ get_recipe_detail(recipe_id)
   │   └─ Retrieve cached recipe
   │
   ├─ cache_recipe_detail(recipe_id, data)
   │   └─ Store recipe detail in Redis
   │
   ├─ get_ingredient_search(ingredient)
   │   └─ Retrieve recipes by ingredient
   │
   ├─ cache_ingredient_search(ingredient, results)
   │   └─ Store ingredient search results
   │
   ├─ get_by_category(category_id)
   │   └─ Get recipes in category
   │
   ├─ cache_by_category(category_id, results)
   │   └─ Store category results
   │
   ├─ get_trending_recipes(timeframe)
   │   └─ Get trending for period
   │
   ├─ cache_trending_recipes(timeframe, results)
   │   └─ Store trending recipes
   │
   ├─ get_user_collection(user_id)
   │   └─ Get user's saved recipes
   │
   ├─ cache_user_collection(user_id, data)
   │   └─ Store user collection
   │
   ├─ invalidate_recipe_cache(recipe_id)
   │   └─ Clear specific recipe cache
   │
   ├─ invalidate_category_cache(category_id)
   │   └─ Clear category cache
   │
   ├─ invalidate_all_search_cache()
   │   └─ Clear all search caches
   │
   └─ clear_all_recipe_cache()
       └─ Clear entire cache (CAREFUL!)


════════════════════════════════════════════════════════════════════════════
CACHE KEY GENERATION EXAMPLE:
════════════════════════════════════════════════════════════════════════════

Search Query: "pasta"
Filters: {"cuisine": "italian", "difficulty": "easy"}

Input:
    query = "pasta"
    filters = {"cuisine": "italian", "difficulty": "easy"}

Processing:
    1. Combine: "pasta|{'cuisine': 'italian', 'difficulty': 'easy'}"
    2. Hash (MD5): abc123def456xyz789...
    3. Add prefix: "recipe:search:"
    
Output:
    Cache Key: recipe:search:abc123def456xyz789

Benefits:
- Short keys (even if query is 1000 chars)
- Same query + filters = same key
- Different filters = different key


════════════════════════════════════════════════════════════════════════════
LOGGING & MONITORING:
════════════════════════════════════════════════════════════════════════════

All cache operations logged to: logs/cache.log

Example log entries:

[INFO] 2024-04-06 10:30:15 | recipes.cache
       ✓ Cached search results for 'pasta'
       Key: recipe:search:abc123def456

[INFO] 2024-04-06 10:30:16 | recipes.cache
       ✓ Cache HIT for search 'pasta'
       Key: recipe:search:abc123def456

[INFO] 2024-04-06 10:32:45 | recipes.cache
       ✗ Cache MISS for search 'carbonara'
       Key: recipe:search:xyz789xyz789

[INFO] 2024-04-06 10:35:00 | recipes.cache
       ✓ Cached recipe detail (ID: 42)
       Key: recipe:detail:42

[INFO] 2024-04-06 10:40:20 | recipes.cache
       ✓ Invalidated recipe detail cache (ID: 42)


════════════════════════════════════════════════════════════════════════════
MEMORY USAGE ESTIMATION:
════════════════════════════════════════════════════════════════════════════

Example cache entry for recipe search:

Key: recipe:search:abc123 → ~50 bytes
Value (JSON): [recipe1, recipe2, ...] → ~4KB per result

For 1000 popular searches × 10 results each:
    1000 keys × 50 bytes = 50KB
    10,000 results × 4KB = 40MB
    Total: ~40-50MB

Redis with 1GB available: Can cache millions of recipes!

Monitor with:
    redis-cli SELECT 1
    redis-cli INFO memory
    redis-cli DBSIZE


════════════════════════════════════════════════════════════════════════════
CONFIGURATION (settings/base.py):
════════════════════════════════════════════════════════════════════════════

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',  ← DB 1 for cache
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,
        },
    }
}

CACHE_TIMEOUT = {
    'recipe_search': 3600,       # 1 hour
    'recipe_detail': 7200,       # 2 hours
    'random_recipe': 1800,       # 30 minutes
    'spoonacular': 86400,        # 24 hours
}
"""

print(ARCHITECTURE)
