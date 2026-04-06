from .base import*
# Load environment variables from .env file
# load the .env file located at the BASE_DIR
env.read_env(BASE_DIR / '.env')
#OVERRIDES: Set development-specific settings from the .env file
SECRET_KEY=env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=True)  # Default to True in development

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
#Override database settings for development,use the local postgres connection defined in .env
DATABASES = {
    'default': {
        'ENGINE': env('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='localhost'),
        'PORT': env('DB_PORT', default='5432'),
    }
}
# in production you will use an actual email service like sendgrid,amazon ses etc
#but for development,use console backend to print emails to the console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # ... other settings ...
#Spoonacular API key from environment variable(.env file,add it there)
SPOONACULAR_API_KEY = os.getenv('SPOONACULAR_API_KEY')
CELERY_WORKER_POOL = 'solo'  # Uncomment for development or add to dev settings
