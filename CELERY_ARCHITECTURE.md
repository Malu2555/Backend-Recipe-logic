"""
CELERY & CRON JOBS - COMPLETE ARCHITECTURE DIAGRAM
===================================================

HIGH-LEVEL FLOW
===============

┌─────────────────────────────────────────────────────────────────┐
│                      DJANGO APPLICATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  HTTP Request (User Registration)                               │
│         ↓                                                         │
│  users.views.register_view() → Create User                      │
│         ↓                                                         │
│  Django Signal: post_save (User model)                          │
│         ↓                                                         │
│  users.signals.notify_user_registration()                       │
│         ├─→ send_welcome_email_task.delay(user.id)             │
│         └─→ send_team_notification_task.delay(user.id)         │
│         ↓                                                         │
│  HTTP Response: 201 Created (Immediate!)                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
           Task Queued in Redis (DB 2)
                            ↓
         ┌──────────────────────────────────┐
         │     CELERY WORKER PROCESS        │
         ├──────────────────────────────────┤
         │ Polls Redis for tasks             │
         │ Executes send_welcome_email_task │
         │ Executes send_team_notification  │
         │ Stores result in Redis (DB 3)    │
         └──────────────────────────────────┘


OTHER ENDPOINTS (No Email Task Queue)
========================================

┌──────────────────────────────────────────────────────┐
│         SAVED RECIPES ENDPOINT (Synchronous)        │
├──────────────────────────────────────────────────────┤
│                                                       │
│ GET    /api/saved-recipes/   → List user's recipes │
│ POST   /api/saved-recipes/   → Save new recipe     │
│ GET    /api/saved-recipes/1/ → Get one recipe      │
│ PUT    /api/saved-recipes/1/ → Update recipe       │
│ DELETE /api/saved-recipes/1/ → Delete recipe       │
│                                                       │
│ ✓ No email, no caching (uses PostgreSQL)           │
│ ✓ Direct database queries (50-100ms)               │
│ ✓ User-scoped (owner isolation per request.user)   │
│ ✓ Persistent storage (survives app restart)        │
│                                                       │
└──────────────────────────────────────────────────────┘


SCHEDULED TASKS (CRON JOBS)
===========================

┌──────────────────────────────────────────────────────┐
│            CELERY BEAT SCHEDULER                     │
├──────────────────────────────────────────────────────┤
│                                                        │
│  Daily at 1:00 AM UTC                                │
│  └─→ generate_cache_stats_task.delay()              │
│      └─→ Generates cache statistics                 │
│                                                        │
│  Daily at 2:00 AM UTC                                │
│  └─→ cleanup_expired_cache_task.delay()             │
│      └─→ Removes cache entries older than 30 days  │
│                                                        │
└──────────────────────────────────────────────────────────┘
            ↓
    Redis Task Queue (DB 2)
            ↓
      Celery Worker picks up
            ↓
        Task executes
            ↓
      Result stored in Redis (DB 3)


COMPLETE MESSAGE FLOW
=====================

1. USER REGISTERS (Synchronous)
   ────────────────────────────
   
   Browser: POST /api/users/register/
      ↓
   Django: users.views.register_view()
      ↓
   Database: Create User instance
      ↓
   Signal: users.signals.notify_user_registration()
      ├─→ Queue: send_welcome_email_task
      │            ↓
      │      Redis (DB 2) ← TASK QUEUED (Fast!)
      │
      └─→ Queue: send_team_notification_task
                 ↓
           Redis (DB 2) ← TASK QUEUED (Fast!)
      ↓
   Django: Return HTTP 201 (Immediate response)
      ↓
   Browser: User Registration Complete


2. CELERY WORKER PROCESSES TASKS (Asynchronous)
   ────────────────────────────────────────────
   
   Celery Worker: polls Redis (DB 2)
      ↓
   Finds: send_welcome_email_task
      ↓
   Execute: users/tasks.py::send_welcome_email_task()
      ├─→ Get user from database
      ├─→ Compose email
      ├─→ Send via SMTP
      └─→ Log result
      ↓
   Store Result: Redis (DB 3)
      ↓
   Celery Worker: polls Redis (DB 2)
      ↓
   Finds: send_team_notification_task
      ↓
   Execute: users/tasks.py::send_team_notification_task()
      ├─→ Get user from database
      ├─→ Compose email
      ├─→ Send via SMTP
      └─→ Log result
      ↓
   Store Result: Redis (DB 3)


3. SCHEDULED TASKS (Cron Jobs)
   ──────────────────────────
   
   Celery Beat: Checks schedule every minute
      ↓
   Current time: 2024-04-06 02:00:00 UTC
      ↓
   Match found: cleanup_expired_cache_task
      ├─→ Queue task to Redis (DB 2)
      └─→ Mark as pending
      ↓
   Celery Worker: Picks up from queue
      ↓
   Execute: recipes/tasks.py::cleanup_expired_cache_task(days=30)
      ├─→ Query SpoonacularCache model
      ├─→ Find entries older than 30 days
      ├─→ Delete stale entries from Redis DB 1
      └─→ Log results
      ↓
   Store Result: Redis (DB 3)
      ↓
   Return: {'status': 'success', 'deleted_count': 42}


4. SAVE RECIPE (Synchronous, No Email Task)
   ──────────────────────────────────────
   
   Browser: POST /api/saved-recipes/
   {
     "title": "Pasta Carbonara",
     "instructions": "Cook pasta...",
     "spoonacular_id": 12345
   }
      ↓
   Django: Verify JWT token (IsAuthenticated permission)
      ↓
   Validate: LocalRecipeSerializer
      ├─→ title: required
      ├─→ instructions: required
      └─→ spoonacular_id: required
      ↓
   Database: INSERT into recipes_localrecipe
   (owner_id=request.user.id, title, instructions, 
    spoonacular_id, created_at)
      ↓
   Serialize: LocalRecipeSerializer
   {
     "id": 1,
     "title": "Pasta Carbonara",
     "instructions": "Cook...",
     "spoonacular_id": 12345,
     "owner": 5,
     "owner_username": "john_doe"
   }
      ↓
   Response: 201 Created with recipe JSON
      ↓
   Browser: Recipe Saved to Database
   
   NOTE: No email task queued, no caching
   Direct DB insert, user-scoped via owner filter


COMPONENT INTERACTION DIAGRAM
=============================

┌───────────────────────────────────────────────────────────────┐
│                   PROJECT_TWO DJANGO APP                      │
├──────────────┬──────────────────────────────────────┬──────────┤
│              │                                      │           │
│  Views       │  Signals                    │ Tasks  │ Settings │
│              │                                      │           │
│ register     │ notify_user_registration()─┐ │ users/│          │
│              │         (Queues Email)     │ │ tasks.│ dev.py   │
│              │                        │   │ │ py    │ Email:   │
│              │                        └─→ │ │       │ Backend: │
│              │                            │ └─────→│ console  │
│              │                            │        │          │
│ saved_recipes│ (No signals, direct DB)             │ prod.py  │
│              │                                      │ Email:   │
│              │ LocalRecipeViewSet ────────────────→│ Backend: │
│              │ (owner filter)                       │ SendGrid │
│              │ (no email task)                      │ (API)    │
│              │                                      │          │
└──────────────┴──────────────────────────────────────┴──────────┘
                                                  ↓
                         ┌───────────────────────────────────┐
                         │  REDIS MESSAGE BROKER & DB        │
                         ├───────────────────────────────────┤
                         │ DB 0: Channels (WebSockets)       │
                         │ DB 1: Recipe Cache (Search/detail)│
                         │ DB 2: Task Queue (Broker)      ←──┼── Email tasks
                         │ DB 3: Result Backend          ←───┼── Results
                         │                                   │
                         │ Note: Saved recipes use           │
                         │ PostgreSQL (not Redis cache)      │
                         └───────────────────────────────────┘
                                        ↓
        ┌───────────────────────────────────────────────────┐
        │          CELERY WORKER PROCESS(ES)                │
        ├───────────────────────────────────────────────────┤
        │ ┌─────────────────────────────────────────────┐   │
        │ │ Task Consumer Thread 1                      │   │
        │ │ Executes: send_welcome_email_task           │   │
        │ │ Status: Processing...                       │   │
        │ └─────────────────────────────────────────────┘   │
        │                                                     │
        │ ┌─────────────────────────────────────────────┐   │
        │ │ Task Consumer Thread 2                      │   │
        │ │ Executes: send_team_notification_task       │   │
        │ │ Status: Completed                           │   │
        │ └─────────────────────────────────────────────┘   │
        │                                                     │
        │ ┌─────────────────────────────────────────────┐   │
        │ │ Task Consumer Thread 3                      │   │
        │ │ Status: Waiting for tasks...                │   │
        │ └─────────────────────────────────────────────┘   │
        └───────────────────────────────────────────────────┘
                        ↓
        ┌───────────────────────────────────────────────┐
        │  SMTP SERVER (Send Emails)                    │
        ├───────────────────────────────────────────────┤
        │ ✓ Welcome email sent to user@example.com      │
        │ ✓ Notification sent to maludev26@gmail.com    │
        └───────────────────────────────────────────────┘


        ┌───────────────────────────────────────────────────┐
        │         CELERY BEAT SCHEDULER                     │
        ├───────────────────────────────────────────────────┤
        │ Runs every minute, checks schedule:              │
        │                                                    │
        │ 1:00 AM? → cleanup_expired_cache_task            │
        │ 2:00 AM? → generate_cache_stats_task             │
        │                                                    │
        │ Current time: 2:00:00 AM ✓ Match!               │
        │ → Queue task to Redis DB 2                       │
        │ → Celery Worker picks it up                      │
        │ → Task executes                                  │
        │ → Result stored in Redis DB 3                    │
        └───────────────────────────────────────────────────┘


FILE STRUCTURE & RESPONSIBILITIES
==================================

project_two/
├── celery.py                    ← Main Celery app config
├── celery_config.py             ← Beat schedule definitions
├── settings/
│   └── base.py                  ← Celery settings (broker, backend, etc.)
├── users/
│   ├── signals.py               ← Queue tasks on user creation (MODIFIED)
│   └── tasks.py                 ← Define email tasks (NEW)
├── recipes/
│   ├── tasks.py                 ← Define cron job tasks (NEW)
│   └── management/commands/
│       └── cleanup.py           ← Original sync command (still works)
└── Documentation/
    ├── CELERY_SETUP_GUIDE.md           ← Full documentation
    ├── CELERY_QUICK_REFERENCE.md       ← Quick commands
    ├── CELERY_IMPLEMENTATION_SUMMARY.md ← This file
    └── CELERY_REQUIREMENTS.txt         ← Package list


TASK STATUS TRANSITIONS
=======================

When a task is queued:

PENDING → (Worker picks up) → STARTED → SUCCESS or FAILURE
   ↓                                           ↓
(Waiting for                            (Result stored
 worker)                             in Redis DB 3)


QUEUE ISOLATION (Optional)
==========================

Tasks can be routed to different queues:

CELERY_TASK_ROUTES = {
    'users.tasks.*': {'queue': 'email'},       # All user tasks → email queue
    'recipes.tasks.*': {'queue': 'maintenance'} # All recipe tasks → maintenance queue
}

You can then run separate workers for each queue:

# Worker 1: Only process email tasks
celery -A project_two worker -l info -Q email

# Worker 2: Only process maintenance tasks
celery -A project_two worker -l info -Q maintenance


MONITORING & OBSERVABILITY
===========================

Log Files:
    logs/
    ├── app.log           ← All app logs
    ├── signals.log       ← Signal execution logs
    ├── cache.log         ← Cache operation logs
    ├── errors.log        ← Error logs
    └── ...

Real-time Monitoring:
    celery -A project_two events
    celery -A project_two inspect active
    flower -A project_two

Redis Monitoring:
    redis-cli
    > KEYS "*"     # See all keys
    > DBSIZE       # Database size
    > MONITOR      # Real-time command monitoring


EMAIL BACKEND CONFIGURATION
============================

DEVELOPMENT (settings/dev.py):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    
    ✓ Emails print to terminal/console
    ✓ No SMTP connection needed
    ✓ Instant delivery to console
    ✓ Easy debugging (see email content)
    
    Example output:
    >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    Subject: Welcome to Our Recipes App!
    To: john@example.com
    
    Hello John,
    
    Welcome to our Recipes Community! 🎉
    <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<


PRODUCTION (settings/prod.py):
    EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
    DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
    
    ✓ Sends real emails via SendGrid API
    ✓ API key stored in secret manager
    ✓ Handles retries automatically (Celery handles)
    ✓ SendGrid tracks opens, clicks, bounces
    ✓ ~100-200ms per email via API
    
    No code changes needed! Task automatically uses
    the EMAIL_BACKEND configured in settings.


KEY/SAVED RECIPES ENDPOINT (No Email)
=====================================

POST /api/saved-recipes/ → LocalRecipeViewSet
    ✓ Synchronous (no Celery)
    ✓ Direct database (PostgreSQL)
    ✓ User-scoped via get_queryset()
    ✓ Owner auto-assigned in perform_create()
    ✓ No email task queued
    ✓ Response: ~100-150ms

GET /api/saved-recipes/ → LocalRecipeViewSet
    ✓ User-filtered queryset
    ✓ Response: ~50-100ms
    ✓ No caching (always fresh)
    ✓ Persistent data


KEY FEATURES SUMMARY
====================

✓ Non-blocking email sending (user sees instant response)
✓ Automatic retry on failure (up to 3 times with exponential backoff)
✓ Scheduled/cron tasks (daily cache cleanup)
✓ Task status tracking (pending, started, success, failed)
✓ Result persistence (stored in Redis DB 3 for 24hrs)
✓ Logging integration (see all task executions)
✓ Error handling (failed tasks logged properly)
✓ Django admin integration (via django-celery-beat)
✓ Monitoring tools (Flower web UI, celery events)
✓ Graceful error recovery (exponential backoff)
✓ Production-ready email backend (SendGrid, SES, etc)
✓ User-scoped saved recipes (no email needed)
"""
