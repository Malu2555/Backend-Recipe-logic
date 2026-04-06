"""
URL configuration for project_two project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
     path('admin/', admin.site.urls),
    path('api/v1/recipes/', include('recipes.urls')),#for versioning your api,i use v1 here
    path('api/v1/', include('users.urls')),#users endpoints (register, list, detail, me, set-password)
    # for browsable api login/logout,direct login to the browsable api login page
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/v1/external/',include("recipes.api.spoonacular_urls")),
   # path('health/', include('recipes.utils.health_check_urls'))
]
# only added during development
if settings.DEBUG:
    urlpatterns+= static(settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT)