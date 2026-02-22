from django.apps import AppConfig
'''This app handles/owns authentication and registration,profile management,password resets etc
specifically for your recipe app's users'''

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
