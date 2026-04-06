# this file handles a users's wish to save data into a permanent db
#It saves the cached data into a permanent table 
#The localRecipe import makes sure this process possible,make sure it has been has been defined
from api.spoonacular_services import get_optimized_recipe
from .models import LocalRecipe

"""Takes a spoonacular ID, fetches(or pulls from the cache),and saves a
permanent copy in postgres for the user """

def convert_eternal_to_local(user,spoon_id):
#1. Get the data(This handles the check DB->Fetch API logic internally)
   raw_data= get_optimized_recipe(spoon_id)if not raw_data else None

#2.Check if the User already saved this(prevent duplicates)
   existing=LocalRecipe.objects.filter(owner=user,spoonacular_id=spoon_id).first() 
   if existing:return existing
#3.Create the Permanent record in your PostgresDB
   new_recipe=LocalRecipe.objects.create(
      owner=user,
      spoonacular_id=spoon_id,
      title=raw_data.get("title"),
      instructions=raw_data.get("instructions"),
      cooking_time=raw_data.get("readyInMinutes",0),
      servings=raw_data.get("servings",1),
      image_url=raw_data.get("image")
   )

   return new_recipe
    