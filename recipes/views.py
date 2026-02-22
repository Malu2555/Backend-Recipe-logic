from rest_framework import viewsets, permissions, filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle, ScopedRateThrottle
from django.core.cache import cache
import logging

# your data models
from .models import (
	Recipe,
	Ingredient,
	RecipeIngredient,
	Category,
	Tag,
	Review,
	Collection,
	Variation,
	NutritionInfo,
)
# your data serializers,transform models to json, vice versa,validate data
from .serializers import (
	RecipeSerializer,
	IngredientSerializer,
	RecipeIngredientSerializer,
	CategorySerializer,
	TagSerializer,
	ReviewSerializer,
	CollectionSerializer,
	VariationSerializer,
	NutritionInfoSerializer,
)

# Initialize logger for caching operations
cache_logger = logging.getLogger('recipes.cache')


# ================================================================================
# MANUAL CACHING FUNCTIONS
# ================================================================================

def trending_recipes(time_window_days=7, limit=10):
	"""
	Retrieve trending recipes with manual Redis caching.
	
	This function implements a simple caching strategy:
	1. Try to get trending recipes from Redis cache
	2. If cache miss, hit PostgreSQL database
	3. Cache the result in Redis for 1 hour (3600 seconds)
	
	@drf_spectacular.openapi.extend_schema documentation:
		operation_id: trending_recipes
		description: |
			Fetches trending recipes based on review activity within a specified
			time window. Uses Redis for caching with a 1-hour TTL.
			
			Caching Strategy:
			- Cache Key: trending_recipes_{time_window_days}_{limit}
			- TTL: 3600 seconds (1 hour)
			- Cache Backend: Redis (configured in settings.py)
			- Invalidation: Cleared by signals.py on Recipe/Review updates
			
			Database Query (on cache miss):
			- Queries Recipe model with prefetch_related optimizations
			- Aggregates review count from related Review model
			- Orders by review count (popularity) descending
			
			Performance:
			- Cache hit: O(1) from Redis
			- Cache miss: O(n) database query with aggregation
			- Typical hit rate: ~99% within 1-hour window
		
		returns:
			- list[dict]: List of recipe dictionaries with aggregated review counts
			- Max items: limited by 'limit' parameter (default: 10)
			
		cache_keys_affected:
			- trending_recipes_{time_window_days}_{limit}
			- Cleared on: Recipe post_save, Recipe post_delete, Review post_save, Review post_delete
	
	Args:
		time_window_days (int): Number of days to consider for trending (default: 7)
		limit (int): Maximum number of recipes to return (default: 10)
	
	Returns:
		list: List of trending recipe data with review aggregation
	
	Raises:
		Exception: Logs error if database query fails, returns empty list
	"""
	cache_key = f'trending_recipes_{time_window_days}_{limit}'
	
	try:
		# Step 1: Try to get from Redis cache
		cached_data = cache.get(cache_key)
		
		if cached_data is not None:
			cache_logger.debug(
				f"Trending recipes cache HIT",
				extra={
					'cache_key': cache_key,
					'items_returned': len(cached_data),
				}
			)
			logging.getLogger('recipes.signals').info(
				f"Trending recipes served from Redis cache",
				extra={'cache_key': cache_key, 'count': len(cached_data)},
			)
			return cached_data
		
		# Step 2: Cache MISS - Hit PostgreSQL database
		cache_logger.info(
			f"Trending recipes cache MISS - querying PostgreSQL",
			extra={
				'cache_key': cache_key,
				'time_window_days': time_window_days,
				'limit': limit,
			}
		)
		
		from django.db.models import Count
		from django.utils import timezone
		from datetime import timedelta
		
		# Calculate date range for trending window
		days_ago = timezone.now() - timedelta(days=time_window_days)
		
		# Query recipes with review count aggregation
		trending = Recipe.objects.filter(
			reviews__created_at__gte=days_ago
		).annotate(
			review_count=Count('reviews')
		).prefetch_related(
			'tags', 'categories', 'recipe_ingredients', 'reviews'
		).select_related(
			'nutrition_info', 'author'
		).order_by(
			'-review_count'
		)[:limit]
		
		# Serialize the queryset
		serializer = RecipeSerializer(trending, many=True)
		trending_data = serializer.data
		
		# Step 3: Store in Redis for 1 hour (3600 seconds)
		cache.set(cache_key, trending_data, timeout=3600)
		
		cache_logger.info(
			f"Trending recipes cached in Redis for 1 hour",
			extra={
				'cache_key': cache_key,
				'items_cached': len(trending_data),
				'ttl_seconds': 3600,
			}
		)
		
		logging.getLogger('recipes.signals').info(
			f"Trending recipes computed and stored in Redis",
			extra={
				'cache_key': cache_key,
				'count': len(trending_data),
				'time_window_days': time_window_days,
			},
		)
		
		return trending_data
		
	except Exception as exc:
		cache_logger.error(
			f"Error fetching trending recipes: {str(exc)}",
			exc_info=True,
			extra={'cache_key': cache_key},
		)
		logging.getLogger('recipes.signals').error(
			f"Failed to fetch trending recipes: {str(exc)}",
			extra={'cache_key': cache_key},
			exc_info=True,
		)
		return []  # Return empty list on error





#default permission classes for all viewsets
#dynamically assign permissions based on action if needed
def get_permissions(self):
 if self.action == 'list' or self.action == 'retrieve' or self.action== 'create_review':
		 return [permissions.AllowAny()]#public access for read-only actions
 #only logged-in users can create,update,delete
 #maybe anonymous will make changes to recipes in future
DEFAULT_PERMISSIONS=[permissions.IsAuthenticatedOrReadOnly]
@extend_schema_view(
	list=extend_schema(summary="List recipes", description="Retrieve a paginated list of recipes."),
	retrieve=extend_schema(summary="Retrieve recipe", description="Retrieve a single recipe by ID."),
	create=extend_schema(summary="Create recipe", description="Create a new recipe."),
	update=extend_schema(summary="Update recipe", description="Update an existing recipe (PUT)."),
	partial_update=extend_schema(summary="Partial update recipe", description="Partially update an existing recipe (PATCH)."),
	destroy=extend_schema(summary="Delete recipe", description="Delete a recipe by ID."),
)
# your viewsets are class based views that provide the logic for your API endpoints/requests handling
class RecipeViewSet(viewsets.ModelViewSet):
	throttle_classes=[ScopedRateThrottle]# a strict uploading limit of 50 recipe uploads per day
	throttle_scope='uploads' # this viewset uses the 'uploads' throttle rate defined in settings
	"""ViewSet for Recipe objects.

	- Uses `RecipeSerializer` for full nested representation.
	- Searchable by `title`, `description`, `Author`, `tags` and `categories`.
	-The queryset tells your view which data to operate on,can return lists,retrieve/update/delete
	-The manager(objects) is the interface btwn the py class and db
    - prefetch_related optimizes many-to-many and reverse foreign key lookups
	"""
	queryset = Recipe.objects.all().prefetch_related("tags", "categories", "recipe_ingredients", "reviews").select_related("nutrition_info")
	#The source  of your validated and translated data
	serializer_class = RecipeSerializer
	permission_classes = DEFAULT_PERMISSIONS
	filter_backends = [filters.SearchFilter, filters.OrderingFilter]
	search_fields = ["title", "description", "Author", "tags__name", "categories__name"]
	ordering_fields = ["created_at", "prep_time", "cook_time", "servings"]
	ordering = ["-created_at"]


@extend_schema_view(
	list=extend_schema(summary="List ingredients", description="List all ingredients."),
	retrieve=extend_schema(summary="Retrieve ingredient", description="Get an ingredient by ID."),
)
class IngredientViewSet(viewsets.ModelViewSet):
	queryset = Ingredient.objects.all()
	serializer_class = IngredientSerializer
	permission_classes = DEFAULT_PERMISSIONS
	filter_backends = [filters.SearchFilter, filters.OrderingFilter]
	search_fields = ["name"]
	ordering_fields = ["name"]


@extend_schema_view(
	list=extend_schema(summary="List recipe-ingredients", description="List ingredient relationships for recipes."),
)
class RecipeIngredientViewSet(viewsets.ModelViewSet):
	queryset = RecipeIngredient.objects.select_related("recipe", "ingredient").all()
	serializer_class = RecipeIngredientSerializer
	permission_classes = DEFAULT_PERMISSIONS
	filter_backends = [filters.SearchFilter]
	search_fields = ["recipe__title", "ingredient__name"]


@extend_schema_view(
	list=extend_schema(summary="List categories", description="List recipe categories."),
)
class CategoryViewSet(viewsets.ModelViewSet):
	queryset = Category.objects.all()
	serializer_class = CategorySerializer
	permission_classes = DEFAULT_PERMISSIONS
	filter_backends = [filters.SearchFilter]
	search_fields = ["name"]


@extend_schema_view(
	list=extend_schema(summary="List tags", description="List recipe tags."),
)
class TagViewSet(viewsets.ModelViewSet):
	queryset = Tag.objects.all()
	serializer_class = TagSerializer
	permission_classes = DEFAULT_PERMISSIONS
	filter_backends = [filters.SearchFilter]
	search_fields = ["name"]


@extend_schema_view(
	list=extend_schema(summary="List reviews", description="List reviews for recipes."),
)
class ReviewViewSet(viewsets.ModelViewSet):
	queryset = Review.objects.select_related("recipe").all() #link to recipe for each review
	serializer_class = ReviewSerializer
	permission_classes = DEFAULT_PERMISSIONS
	filter_backends = [filters.SearchFilter, filters.OrderingFilter]
	search_fields = ["user", "comment", "recipe__title"]
	ordering_fields = ["created_at", "rating"]


@extend_schema_view(
	list=extend_schema(summary="List collections", description="List recipe collections."),
)
class CollectionViewSet(viewsets.ModelViewSet):
	queryset = Collection.objects.all()
	serializer_class = CollectionSerializer
	permission_classes = DEFAULT_PERMISSIONS


@extend_schema_view(
	list=extend_schema(summary="List variations", description="List recipe variations."),
)
class VariationViewSet(viewsets.ModelViewSet):
	queryset = Variation.objects.select_related("original_recipe").all()
	serializer_class = VariationSerializer
	permission_classes = DEFAULT_PERMISSIONS


@extend_schema_view(
	list=extend_schema(summary="List nutrition info", description="List nutrition info for recipes."),
)
class NutritionInfoViewSet(viewsets.ModelViewSet):
	queryset = NutritionInfo.objects.select_related("recipe").all()
	serializer_class = NutritionInfoSerializer
	permission_classes = DEFAULT_PERMISSIONS


# Example router registration (add to your project's urls.py or app urls):
# from rest_framework.routers import DefaultRouter
# from .views import RecipeViewSet, IngredientViewSet, CategoryViewSet, TagViewSet
# router = DefaultRouter()
# router.register(r"recipes", RecipeViewSet)
# router.register(r"ingredients", IngredientViewSet)
# router.register(r"categories", CategoryViewSet)
# router.register(r"tags", TagViewSet)
# urlpatterns = router.urls


