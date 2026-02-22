# app level url routing system
from django.urls import include, path
from rest_framework.routers import DefaultRouter
#import viewsets from views.py
from .views import (
	RecipeViewSet,
	IngredientViewSet,
	RecipeIngredientViewSet,
	CategoryViewSet,
	TagViewSet,
	ReviewViewSet,
	CollectionViewSet,
	VariationViewSet,
	NutritionInfoViewSet,
)
#use default router to auto create routes for your viewsets
router = DefaultRouter()
router.register(r"recipes", RecipeViewSet, basename="recipe")
router.register(r"ingredients", IngredientViewSet, basename="ingredient")
router.register(r"recipe-ingredients", RecipeIngredientViewSet, basename="recipeingredient")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"tags", TagViewSet, basename="tag")
router.register(r"reviews", ReviewViewSet, basename="review")
router.register(r"collections", CollectionViewSet, basename="collection")
router.register(r"variations", VariationViewSet, basename="variation")
router.register(r"nutrition", NutritionInfoViewSet, basename="nutrition")

#you dont need to define each url pattern manually,router does it for you
urlpatterns = [
	path("", include(router.urls)),
]
