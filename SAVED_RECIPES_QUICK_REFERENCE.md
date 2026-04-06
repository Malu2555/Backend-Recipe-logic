"""
SAVED RECIPES ENDPOINT - QUICK SUMMARY
======================================
"""

# ============================================================================
# WHAT WAS ADDED
# ============================================================================

"""
✓ LocalRecipeSerializer      (recipes/serializers.py)
✓ LocalRecipeViewSet         (recipes/views.py)  
✓ URL Router Registration    (recipes/urls.py)
✓ Full Documentation         (SAVED_RECIPES_ENDPOINT.md)

NEW ENDPOINT:  /api/saved-recipes/
"""

# ============================================================================
# QUICK START
# ============================================================================

"""
1. LIST USER'S SAVED RECIPES:
   ─────────────────────────
   GET /api/saved-recipes/
   
   Returns all recipes that current user has saved

2. SAVE A RECIPE:
   ──────────────
   POST /api/saved-recipes/
   {
       "title": "Pasta",
       "instructions": "...",
       "spoonacular_id": 12345
   }
   
   Saves a Spoonacular recipe to user's collection

3. VIEW ONE RECIPE:
   ────────────────
   GET /api/saved-recipes/1/
   
   Returns specific saved recipe details

4. UPDATE A RECIPE:
   ────────────────
   PATCH /api/saved-recipes/1/
   {"title": "Updated title"}
   
   Updates recipe details

5. DELETE A RECIPE:
   ════════════════
   DELETE /api/saved-recipes/1/
   
   Removes recipe from user's collection
"""

# ============================================================================
# KEY FEATURES
# ============================================================================

"""
✓ AUTHENTICATION REQUIRED
  - Only authenticated users can access
  - Each user sees only their own saved recipes

✓ AUTOMATIC OWNER ASSIGNMENT
  - Owner automatically set to current user
  - Cannot save recipes for other users

✓ SEARCH & FILTER
  - Search by title
  - Search by spoonacular_id
  - Sort by id or title

✓ FULL CRUD OPERATIONS
  - Create: Save new recipe
  - Retrieve: Get one recipe
  - Update: Modify recipe details
  - Delete: Remove recipe
  - List: View all saved recipes

✓ DATA PERSISTENCE
  - Recipes stored in LocalRecipe table
  - Data persists between sessions
  - Local database (not dependent on Spoonacular API)

✓ SECURITY
  - queryset filtered by owner=request.user
  - Users can only see/modify their own recipes
  - No cross-user data leakage
"""

# ============================================================================
# ENDPOINT PATHS
# ============================================================================

"""
/api/saved-recipes/                    GET    List all user's saved recipes
                                        POST   Save a new recipe

/api/saved-recipes/{id}/                GET    Get one recipe
                                         PUT    Update recipe (full)
                                         PATCH  Update recipe (partial)
                                         DELETE Delete recipe

/api/saved-recipes/?search=pasta       GET    Search recipes
/api/saved-recipes/?ordering=-id       GET    Sort recipes
"""

# ============================================================================
# USAGE EXAMPLE (JavaScript)
# ============================================================================

"""
// Get token
const r1 = await fetch('/api/token/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email: 'user@example.com', password: 'pass'})
});
const {access} = await r1.json();
const token = access;

// List saved recipes
const r2 = await fetch('/api/saved-recipes/', {
    headers: {'Authorization': `Bearer ${token}`}
});
const data = await r2.json();
console.log(data.results);  // User's saved recipes

// Save new recipe
const r3 = await fetch('/api/saved-recipes/', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        title: 'Pasta Carbonara',
        instructions: 'Cook pasta...',
        spoonacular_id: 12345
    })
});
const saved = await r3.json();
console.log('Saved!', saved);

// Delete recipe
const r4 = await fetch('/api/saved-recipes/1/', {
    method: 'DELETE',
    headers: {'Authorization': `Bearer ${token}`}
});
// 204 No Content = success
"""

# ============================================================================
# TESTING IN SWAGGER UI
# ============================================================================

"""
URL: http://localhost:8000/api/schema/swagger-ui/

Look for:
→ /api/saved_recipes/          (List & Create)
→ /api/saved_recipes/{id}/     (Retrieve, Update, Delete)

Click "Try it out" to test operations!
"""

# ============================================================================
# FILES MODIFIED
# ============================================================================

"""
1. recipes/serializers.py
   - Added: LocalRecipeSerializer
   - Includes: id, title, instructions, spoonacular_id, owner, owner_username
   - Read-only: id, owner, owner_username

2. recipes/views.py
   - Added: LocalRecipeViewSet
   - Features: User filtering, search, ordering, automatic owner assignment
   - Permissions: IsAuthenticated only

3. recipes/urls.py
   - Added: LocalRecipeViewSet import
   - Added: router.register("saved-recipes", LocalRecipeViewSet)

4. recipes/models.py
   - Already has: LocalRecipe model
   - Fields: owner, title, instructions, spoonacular_id
"""

# ============================================================================
# SECURITY FEATURES
# ============================================================================

"""
✓ AUTHENTICATION
  - JWT token required
  - Token expires after 1 hour
  - Refresh token available for renewal

✓ PERMISSION
  - IsAuthenticated permission class
  - Anonymous users get 401 Unauthorized

✓ USER ISOLATION
  - get_queryset() filters by owner=request.user
  - Each user only sees their recipes
  - Cannot access other users' recipes

✓ AUTOMATIC OWNER ASSIGNMENT
  - perform_create() sets owner to request.user
  - User cannot manually set owner field
  - Prevents user from saving recipes as other users
"""

# ============================================================================
# COMMON OPERATIONS
# ============================================================================

"""
SEARCH BY TITLE:
  GET /api/saved-recipes/?search=pasta

SEARCH BY API ID:
  GET /api/saved-recipes/?search=12345

SORT NEWEST FIRST:
  GET /api/saved-recipes/?ordering=-id

SORT A-Z BY TITLE:
  GET /api/saved-recipes/?ordering=title

COMBINE SEARCH & FILTER:
  GET /api/saved-recipes/?search=pasta&ordering=title
"""

# ============================================================================
# ERROR RESPONSES
# ============================================================================

"""
401 UNAUTHORIZED (No token)
  {"detail": "Authentication credentials were not provided."}

403 FORBIDDEN (Cannot update other user's recipe)
  {"detail": "You do not have permission to perform this action."}

404 NOT FOUND (Recipe ID doesn't exist)
  {"detail": "Not found."}

400 BAD REQUEST (Invalid data)
  {"title": ["This field is required."]}
"""

print("""
╔════════════════════════════════════════════════════════════════╗
║        SAVED RECIPES ENDPOINT - QUICK REFERENCE               ║
╚════════════════════════════════════════════════════════════════╝

URL:                /api/saved-recipes/
AUTHENTICATION:     JWT Token Required (IsAuthenticated)
METHODS:            GET, POST, PUT, PATCH, DELETE
DATA MODEL:         LocalRecipe (owner, title, instructions, spoonacular_id)

NEW CAPABILITIES:

✓ Users can save recipes from Spoonacular API
✓ View all recipes they've saved
✓ Update saved recipe details
✓ Delete saved recipes
✓ Search saved recipes by title or ID
✓ Sort saved recipes

SECURITY:
✓ Each user only sees their own recipes
✓ Owner automatically set to current user
✓ Authentication required for all operations

DOCUMENTATION:
→ Read: SAVED_RECIPES_ENDPOINT.md (full reference)
→ Test: http://localhost:8000/api/schema/swagger-ui/

FILES CREATED:
✓ SAVED_RECIPES_ENDPOINT.md (comprehensive guide)
✓ Serializer in recipes/serializers.py
✓ ViewSet in recipes/views.py
✓ URL route in recipes/urls.py
""")
