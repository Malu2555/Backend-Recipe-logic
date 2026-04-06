from django.contrib import admin
from .api.spoonacular_cachemodel import SpoonacularCache

# Register your models here.
from .models  import(
    LocalRecipe,
    Recipe,
    Ingredient,
    RecipeIngredient,
    Category,
    Tag,
    Collection,
    Variation,
    Review,
    NutritionInfo,)

@admin.register(SpoonacularCache)
class SpoonacularCacheAdmin(admin.ModelAdmin):
    #what columns to show in the list view
    list_display=('recipe_id','is_stale_status')
    #allow searching by RecipeID
    search_fields=('recipe_id',)
    #add a filter on the right sidebar
    list_filter=('recipe_id',)
    #Custom method to show a green/red light for staleness
    def is_stale_status(self,obj):
        return obj.is_stale()
    is_stale_status.boolean=True
    is_stale_status.short_description='Is Stale?'

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'prep_time')
    search_fields = ('title', 'description', 'Author')
    list_filter = ('created_at',) 
@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'quantity')
    search_fields = ('name',)  
@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):  
    list_display = ('recipe', 'ingredient')
    search_fields = ('recipe__title',)
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'user', 'rating', 'created_at')
    search_fields = ('rating',)
    list_filter = ('rating', 'created_at',)
@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
@admin.register(Variation)
class VariationAdmin(admin.ModelAdmin):
    list_display = ('title', 'original_recipe') #controls which fields to view in the admin panel.
    search_fields = ('title',)
@admin.register(NutritionInfo)
class NutritionInfoAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'calories', 'protein')
    search_fields = ('recipe',)
'''Instead of using admin.site.register(modelname)I used an admin decorator,created obj and
used list_display to see actual data in the admin panel(converts obj into human readable cont)
The --str--func in models.py helps in making the objects to be readable'''