from django.apps import AppConfig
'''This app handles/owns authentication and registration,profile management,password resets etc
specifically for your recipe app's users'''

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        #to ensure signal handlers are registered before django starts(more on this later,prob message brokers)
        
        import users.signals
