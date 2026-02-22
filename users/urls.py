from django.urls import path, include
from rest_framework.routers import DefaultRouter
# importing JWT views for handling token-based authentication,you don't have to write these views yourself
from .views import UserViewSet,CustomTokenObtainPairView,LogoutView,CustomTokenRefreshView
# Setting up a router to automatically handle URL routing for the UserViewSet
# This will create endpoints for user registration, listing, detail view, current user info, and password change
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns =[
    #handles the "platform" flag for web vs mobile
    path('api/login/',CustomTokenObtainPairView.as_view(),name='token_obtain_pair'),# login endpoint,users can successfully login and obtain JWT tokens
    path('api/login/refresh/',CustomTokenRefreshView.as_view(),name='token_refresh'),# token refresh endpoint,automatically checkng cookies
    path('api/logout/',LogoutView.as_view(),name='auth_logout'),# logout endpoint,handles cookie deletion and token blacklisting
    path('',include(router.urls)),
]
