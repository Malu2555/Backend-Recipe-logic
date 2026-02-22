"""
ASGI config for project_two project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application
#1.Set the settings module to your split dev file
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_two.settings.dev')

#2. INITIALIZE DJANGO FIRST,START DJANGO FIRST B4 YOUR WEBSOCKET TRIES TO USE IT
#-This is the secret sauce for custom user models.
#get_asgi_application()calls django.setup() internally,starter motor to enable the django setup

django_asgi_app=get_asgi_application()# passed in a variable and mapped to http key

#3. NOW IMPORT CHANNELS(after django is ready)
from channels.routing import ProtocolTypeRouter,URLRouter
from channels.auth import AuthMiddlewareStack

#4.IMPORT YOUR APP ROUTING
import recipes.routing

application=ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket':AuthMiddlewareStack(URLRouter(
        recipes.routing.websocket_urlpatterns
    )),
})
'''Since you have a custom user,the AuthMiddlewareStack needs to look at your DB to authenticate users
if get_asgi_application is not called first,the middleware won't know your CustomUser exists'''