from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field, OpenApiTypes
from django.db import transaction
import numbers
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

#instead of using depth=1 etc,define "child" serializers above the "parent" serializer
#This way we can reference them directly in the parent serializer if needed
#this is how you handle  data transformation and validation in DRF,by using serializers
class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name", "quantity"]
        extra_kwargs = {
            "name": {"help_text": "Ingredient name (string)"},
            "quantity": {"help_text": "Ingredient quantity/measure (string)"},
        }


class RecipeIngredientSerializer(serializers.ModelSerializer):
    # allow nested ingredient payloads on create/update
    ingredient = IngredientSerializer()

    class Meta:
        model = RecipeIngredient
        fields = ["id", "ingredient", "quantity"]
        extra_kwargs = {
            "quantity": {"help_text": "Quantity for this ingredient (float)"},
        }


class NutritionInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionInfo
        fields = ["id", "calories", "fat", "protein", "carbohydrates"]
        extra_kwargs = {
            "calories": {"help_text": "Calories (integer)"},
            "fat": {"help_text": "Fat in grams (float)"},
            "protein": {"help_text": "Protein in grams (float)"},
            "carbohydrates": {"help_text": "Carbohydrates in grams (float)"},
        }


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "user", "rating", "comment", "created_at", "is_official"]
        read_only_fields = ["created_at", "is_official"]
        extra_kwargs = {
            "user": {"help_text": "User name (string)"},
            "rating": {"help_text": "Rating from 1 to 5 (integer)"},
            "comment": {"help_text": "Optional review comment (string)"},
        }


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]
        extra_kwargs = {
            "name": {"help_text": "Category name (string)"},
            "description": {"help_text": "Category description (string)"},
        }


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]
        extra_kwargs = {"name": {"help_text": "Tag name (string)"}}


class VariationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variation
        fields = ["id", "original_recipe", "title", "description", "instructions", "created_at", "is_official"]
        read_only_fields = ["created_at", "is_official"]
        extra_kwargs = {
            "title": {"help_text": "Variation title (string)"},
            "description": {"help_text": "Variation description (string)"},
            "instructions": {"help_text": "Variation instructions (string)"},
        }


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = ["id", "name", "description"]
        extra_kwargs = {
            "name": {"help_text": "Collection name (string)"},
            "description": {"help_text": "Collection description (string)"},
        }


class RecipeSerializer(serializers.ModelSerializer):# the parent serializer for recipes,all other related serializers are nested within this
    # make recipe_ingredients writable so nested data can be provided when creating a recipe
    #this pulls the username from the linked user model
    # in models.py,author is okay,in serializer use author_username to get the name field from linked user model instead of id
    author_username = serializers.CharField(source='author.name', read_only=True)
    author_image = serializers.ImageField(source='author.profile_image', read_only=True)
    recipe_ingredients = RecipeIngredientSerializer(many=True)
    nutrition_info = NutritionInfoSerializer(read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)

    total_ingredients = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        #drf-spectacular will use these fields to generate the schema,even pulling from models.py
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "prep_time",
            "cook_time",
            "servings",
            "instructions",
            "image",
            "Author",# returns the author id
            "author_username",# returns the author name from linked user model
            "recipe_ingredients",
            "nutrition_info",
            "categories",
            "tags",
            "reviews",
            "total_ingredients",
            "average_rating",
            "is_official",
        ]
        read_only_fields = ["created_at", "title", "Author", "is_official"]
        extra_kwargs = {
            "title": {"help_text": "Recipe title (string)"},
            "description": {"help_text": "Short description (string)"},
            "prep_time": {"help_text": "Preparation time in minutes (integer)"},
            "cook_time": {"help_text": "Cooking time in minutes (integer)"},
            "servings": {"help_text": "Number of servings (integer)"},
            "instructions": {"help_text": "Cooking instructions (string)"},
            "image": {"help_text": "Image file for the recipe"},
            "Author": {"help_text": "Author name (string)"},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)# all other class serializers inherit from this main recipe serializer
        # add help_text for method fields so Swagger shows a short description
        if "total_ingredients" in self.fields:
            self.fields["total_ingredients"].help_text = "Total number of ingredients (integer)"
        if "average_rating" in self.fields:
            self.fields["average_rating"].help_text = "Average rating (float)"

    def validate_recipe_ingredients(self, value):
        """Validate nested recipe_ingredients payload shape.

        Expected each item to be a dict containing:
        - `ingredient`: int (id), dict with `id` or `name`, or string (name)
        - `quantity`: numeric (int/float)

        Returns the original list if valid, otherwise raises a ValidationError with
        index-specific messages for easier debugging in OpenAPI clients.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("`recipe_ingredients` must be a list of objects")

        errors = {}
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                errors[i] = "Each ingredient entry must be an object/dict"
                continue

            # ingredient presence and shape
            if "ingredient" not in item:
                errors[i] = "Missing required field: 'ingredient' (id, dict or name)"
            else:
                ing = item.get("ingredient")
                ok = False
                if isinstance(ing, int):
                    ok = True
                elif isinstance(ing, str):
                    ok = bool(ing.strip())
                elif isinstance(ing, dict):
                    if ing.get("id") or ing.get("name"):
                        ok = True
                if not ok:
                    errors[i] = "Invalid 'ingredient' value: must be id, name string, or dict with 'id'/'name'"

            # quantity validation
            if "quantity" not in item:
                errors.setdefault(i, []).append("Missing required field: 'quantity'")
            else:
                qty = item.get("quantity")
                if not isinstance(qty, numbers.Number):
                    # allow numeric strings that can be converted
                    try:
                        float(qty)
                    except Exception:
                        errors.setdefault(i, []).append("'quantity' must be numeric")

        if errors:
            raise serializers.ValidationError({"recipe_ingredients": errors})

        return value

    def validate(self, data):
        """Top-level validation for nutrition payload and any additional constraints."""
        nutrition = data.get("nutrition_info")
        if nutrition is not None:
            if not isinstance(nutrition, dict):
                raise serializers.ValidationError({"nutrition_info": "Must be an object/dict"})
            # ensure numeric fields if provided
            for key in ("calories", "fat", "protein", "carbohydrates"):
                if key in nutrition and nutrition[key] is not None and not isinstance(nutrition[key], numbers.Number):
                    try:
                        float(nutrition[key])
                    except Exception:
                        raise serializers.ValidationError({"nutrition_info": {key: "Must be numeric"}})

        return data

    def create(self, validated_data):
        """Create a Recipe and its nested relations atomically.

        Expected nested payloads:
        - `recipe_ingredients`: list of { "ingredient": {id|name|...} or id, "quantity": float }
        - `categories` / `tags`: list of ids or dicts with `id`/`name` (optional)
        - `nutrition_info`: dict for nutrition fields (optional)
        This method uses `transaction.atomic()` so either everything is saved or nothing is.
        """
        ingredients_data = validated_data.pop("recipe_ingredients", [])
        categories_data = validated_data.pop("categories", [])
        tags_data = validated_data.pop("tags", [])
        nutrition_data = validated_data.pop("nutrition_info", None)

        def _resolve_m2m(model, items):
            instances = []
            for it in items:
                if isinstance(it, int):
                    instances.append(model.objects.get(id=it))
                elif isinstance(it, dict):
                    pk = it.get("id")
                    if pk:
                        instances.append(model.objects.get(id=pk))
                    else:
                        instances.append(model.objects.create(**it))
            return instances

        with transaction.atomic():
            recipe = Recipe.objects.create(**validated_data)

            # handle categories and tags (allow ids or dicts)
            if categories_data:
                recipe.categories.set(_resolve_m2m(Category, categories_data))
            if tags_data:
                recipe.tags.set(_resolve_m2m(Tag, tags_data))

            # nutrition info
            if nutrition_data:
                NutritionInfo.objects.create(recipe=recipe, **nutrition_data)

            # recipe ingredients: allow nested ingredient creation or existing id
            for ri in ingredients_data:
                ingredient_payload = ri.get("ingredient")
                quantity = ri.get("quantity")

                # resolve ingredient
                ingredient_obj = None
                if ingredient_payload is None:
                    # allow flat keys
                    name = ri.get("name")
                    q = ri.get("ingredient_quantity") or ri.get("quantity")
                    if name:
                        ingredient_obj, _ = Ingredient.objects.get_or_create(name=name, defaults={"quantity": q or ""})
                elif isinstance(ingredient_payload, int):
                    ingredient_obj = Ingredient.objects.get(id=ingredient_payload)
                elif isinstance(ingredient_payload, dict):
                    pk = ingredient_payload.get("id")
                    if pk:
                        ingredient_obj = Ingredient.objects.get(id=pk)
                    else:
                        ingredient_obj = Ingredient.objects.create(**ingredient_payload)
                elif isinstance(ingredient_payload, str):
                    ingredient_obj, _ = Ingredient.objects.get_or_create(name=ingredient_payload)

                if ingredient_obj is None:
                    raise serializers.ValidationError({"recipe_ingredients": "Invalid ingredient payload"})

                RecipeIngredient.objects.create(recipe=recipe, ingredient=ingredient_obj, quantity=quantity)

            return recipe

    @extend_schema_field(OpenApiTypes.INT)
    def get_total_ingredients(self, obj):
        return obj.recipe_ingredients.count()

    @extend_schema_field(OpenApiTypes.FLOAT)
    def get_average_rating(self, obj):
        ratings = [r.rating for r in obj.reviews.all() if r.rating is not None]
        if not ratings:
            return None
        return sum(ratings) / len(ratings)
#the saving might be handled by ModelViewSets in views.py or by Modelserializers here
#DRF serializers validate native data types not ORM models/python objects directly
#the deserialization phase handles converting incoming data to native types and validating them

