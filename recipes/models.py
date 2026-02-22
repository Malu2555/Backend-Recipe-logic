from django.db import models
from django.conf import settings# import settings to access auth user model
#add the auth model here
#remember you dont have models yet since havent done migrations yet.

# Create your models here.
'''add blank and null to the  fields to allow empty values for future repopulation,
and avoid migration and development errors
This app is designed for client-side repopulation of data via REST API calls using DRF'''
class Recipe(models.Model):
    title = models.CharField(max_length=200,blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True ,blank=True,null=True)
    prep_time = models.IntegerField(help_text="Preparation time in minutes", blank=True,null=True)
    cook_time = models.IntegerField(help_text="Cooking time in minutes", blank=True,null=True)
    servings = models.IntegerField(help_text="Number of servings", blank=True,null=True)
    instructions = models.TextField(blank=True,null=True)
    image = models.ImageField(upload_to='recipes/', null=True, blank=True)
    #the author is a foreign key to the user model,link recipes to users
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True,null=True)
    # a field that allows us to distinguish between official and user-generated recipes
    is_official = models.BooleanField(default=False, help_text="True if added by admin, False if user-generated")
    #pass a field like title to str method to identify objects to human users
    def __str__(self):
        return self.title
#add another model for ingredients
class Ingredient(models.Model):
    name = models.CharField(max_length=100, blank=True,null=True)
    quantity = models.CharField(max_length=100, blank=True,null=True)
    
    def __str__(self):
        return self.name
#add a many-to-many relationship between Recipe and Ingredient,one  recipe can have many ingredients
class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='recipe_ingredients', blank=True,null=True)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='ingredient_recipes', blank=True,null=True)
    quantity = models.FloatField(max_length=100, blank=True,null=True)
    def __str__(self):
        return f"{self.quantity} of {self.ingredient.name} for {self.recipe.title}"
#add a model for categories to classify recipes
class Category(models.Model):
    #category name e.g Dessert,Main Course,Vegan
    name = models.CharField(max_length=100, blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    #link many recipes to many categories
    recipes = models.ManyToManyField(Recipe, related_name='categories', blank=True)
    def __str__(self):
        return self.name
#add a model for tags,for better search and filtering,cache this data with redis
class Tag(models.Model):
    #tag name e.g Healthy,Quick,Easy,spicy
    name = models.CharField(max_length=50, blank=True,null=True)
    #links many recipes to many tags
    recipes = models.ManyToManyField(Recipe, related_name='tags', blank=True)
    def __str__(self):
        return self.name
'''add a model for user reviews and ratings for recipes,to enhance user engagement
use a foreign key to link reviews to recipes,integrate websockets for real-time updates-use
Django Channels'''

class Review(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='reviews', blank=True,null=True)
    user = models.CharField(max_length=100, blank=True,null=True)
    rating = models.IntegerField(help_text="Rating from 1 to 5", blank=True,null=True)
    comment = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True ,blank=True,null=True)
    is_official = models.BooleanField(default=False, help_text="True if added by admin, False if user-generated")
    def __str__(self):
        return f"Review by {self.user} for {self.recipe.title}"
#add a model for recipe collections,allow users to group recipes into collections
class Collection(models.Model):
    name = models.CharField(max_length=100, blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    recipes = models.ManyToManyField(Recipe, related_name='collections', blank=True)
    def __str__(self):
        return self.name
#add a model for recipe variations,to allow users to create and share variations of existing recipes
class Variation(models.Model): #mchanganyiko
    original_recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='variations', blank=True,null=True)
    title = models.CharField(max_length=200, blank=True,null=True)
    description = models.TextField(blank=True,null=True)
    instructions = models.TextField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True ,blank=True,null=True)
    is_official = models.BooleanField(default=False, help_text="True if added by admin, False if user-generated")
    def __str__(self):
        return f"Variation: {self.title} of {self.original_recipe.title}"
#add a model for recipe nutrition information,to provide users with health-related data
class NutritionInfo(models.Model):  
    recipe = models.OneToOneField(Recipe, on_delete=models.CASCADE, related_name='nutrition_info', blank=True,null=True)
    calories = models.IntegerField(blank=True,null=True)
    fat = models.FloatField(help_text="Fat in grams", blank=True,null=True)
    protein = models.FloatField(help_text="Protein in grams", blank=True,null=True)
    carbohydrates = models.FloatField(help_text="Carbohydrates in grams", blank=True,null=True)
    def __str__(self):
        return f"Nutrition Info for {self.recipe.title}"
#Now register your app and models in admin.py or settings.py to manage them via Django admin interface
