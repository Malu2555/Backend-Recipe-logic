from django.urls import re_path

from . import consumers

# WebSocket URL patterns for the recipes app
# Clients should connect to ws/recipes/<recipe_id>/reviews/ for a single recipe's reviews
websocket_urlpatterns = [
    re_path(r"ws/recipes/(?P<recipe_id>\d+)/reviews/?$", consumers.ReviewConsumer.as_asgi()),
]
