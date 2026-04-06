#This your automated cron job that calls the cleanup logic inside your spoonacular api
from django.core.management.base import BaseCommand
#import the deletion logic from spoonacular_services
from recipes.api.spoonacular_services import clear_expired_spoonacular_cache

class Command(BaseCommand):
    help="clean up old spoonacular cache entries"
    def handle(self,*args,**options):
        #we call the specialist  function from the api folder
        count=clear_expired_spoonacular_cache(days=30)
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted{count}stale recipes.'))
