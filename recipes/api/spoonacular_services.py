#this folder handles  the full lifecycle
#of your spoonacular api integration
#this includes Check->Fetch->save to cachedb->
# Delete stale cache
from django.utils import timezone
from datetime import timedelta
from .spoonacular_cachemodel import SpoonacularCache
import requests
from django.conf import settings

class SpoonacularRawClient:
    #Only handles the http pipeline to the internet
    @staticmethod
    def get_raw_data(recipe_id):
        url = f"https://api.spoonacular.com/recipes/{recipe_id}/information"
        params = {
            'apiKey': settings.SPOONACULAR_API_KEY
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()if response.status_code == 200 else None
    def get_optimized_recipe(recipe_id):
        #The Orchestrator:manages the cache-aside logic.
            cached = SpoonacularCache.objects.filter(recipe_id=recipe_id).first()
            if cached and not cached.is_stale():
                cached.save() # touch it to refresh last_updated
                return cached.data
            
            raw_json = SpoonacularRawClient.get_raw_data(recipe_id)
            if raw_json:
                SpoonacularCache.objects.update_or_create(
                    recipe_id=recipe_id,
                    defaults={'data': raw_json, 'last_updated': timezone.now()})
                return raw_json
            
            def clear_expired_spoonacular_cache(days=30):
            #the cleanup file :Deletes recipes that haven't been accessed in a while (e.g., 30 days)
                expiration_threshold = timezone.now() - timedelta(days=days)  
                deleted_count, _ = SpoonacularCache.objects.filter(last_updated__lt=expiration_threshold).delete()
                return deleted_count


