from rest_framework import serializers
import re

class spoonacularRecipeSerializer(serializers.Serializer):
    #map spoonacular's fields to your api response
    id = serializers.IntegerField()
    title = serializers.CharField()
    image = serializers.URLField()
    readyInMinutes = serializers.IntegerField(required=False, allow_null=True)
    servings = serializers.IntegerField(required=False, allow_null=True)
    sourceUrl = serializers.URLField(required=False, allow_null=True)
    summary = serializers.CharField()
    #nested fields for ingredients and nutrition can be added here if needed
    extendedIngredientCount = serializers.ListField(required=False, allow_null=True)
    usedIngredientCount = serializers.IntegerField()
    def to_representation(self, instance):
        #clean the data before sending it to the client(vue.js), e.g., remove HTML tags from summary
        data=super().to_representation(instance)
        data['summary'] = re.sub('<[^<]+?>', '', data['summary'])
        return data

class RecipeSearchResponseSerializer(serializers.Serializer):
    results = spoonacularRecipeSerializer(many=True)
    totalResults = serializers.IntegerField()
    offset = serializers.IntegerField()
    number = serializers.IntegerField()

class NutrientSerializer(serializers.Serializer):
    name = serializers.CharField()
    amount = serializers.FloatField()
    unit = serializers.CharField()
    percentOfDailyNeeds = serializers.FloatField()

class NutritionSerializer(serializers.Serializer):
    nutrients = NutrientSerializer(many=True)

class RecipeDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    image = serializers.URLField()
    summary = serializers.CharField()
    instructions = serializers.CharField(allow_null=True)
    extendedIngredients = serializers.ListField(child=serializers.DictField())
    nutrition = NutritionSerializer()
    readyInMinutes = serializers.IntegerField()
    servings = serializers.IntegerField()