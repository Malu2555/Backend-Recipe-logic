from django.db import models
#creates an obj that stores fetched json data from spoonacular api for caching purposes
class SpoonacularCache(models.Model):
    recipe_id = models.IntegerField(unique=True)
    data = models.JSONField() #full json response
    created_at = models.DateTimeField(auto_now_add=True)
    spoonacular_id = models.IntegerField(unique=True, db_index=True, null=True) #index for faster lookups
    title = models.CharField(max_length=255,null=True,blank=True)
    image = models.URLField(blank=True)
    data = models.JSONField()  # Store full API response
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed = models.DateTimeField(auto_now=True)
    access_count = models.PositiveIntegerField(default=0)  # Track popularity
    
    class Meta:
        ordering = ['-last_accessed']
        indexes = [
            models.Index(fields=['spoonacular_id']),
            models.Index(fields=['last_accessed']),
        ]

    
    def __str__(self):#instead of returning an Object in the admin panel-> returns the actual json file
        return f"SpoonacularCache(recipe_id={self.recipe_id})"
    # a function that defines how long the cache is valid (e.g., 24 hours)
    #Data id stale after 24 hours, you can adjust this as needed
    def is_stale(self):
        from django.utils import timezone
        import datetime
        return (timezone.now() - self.last_updated) > datetime.timedelta(hours=24)
    
    class Meta:
        # make it easier to find in the admin panel
        verbose_name="Spoonacular Cache Entries"