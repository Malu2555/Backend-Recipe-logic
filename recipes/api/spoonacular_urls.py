from django.urls import path
from .spoonacular_view import SpoonacularDetailView

#we define the namespace here to avoid collisions
urlpatterns=[
    #This will result in /recipes/external/recipe/<id>/
    path('recipe/<int:id>/',SpoonacularDetailView.as_view(),name='spoon-detail')
]
