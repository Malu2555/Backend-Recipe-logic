#a request handler for spoonacular api/api logic endpoints
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from .spoonacular_services import SpoonacularRawClient
from .spoonacular_serializers import  spoonacularRecipeSerializer

class SpoonacularDetailView(APIView):
    def get(self, request, recipe_id):
        #1.Get Data: Check cache first, then fetch from spoonacular if needed, and save to cache
        try:
            raw_data = SpoonacularRawClient(recipe_id)
            if not raw_data:
                return Response({'error': 'Recipe not found'}, status=status.HTTP_404_NOT_FOUND)
            #2.Serialize Data: Map spoonacular's raw json to your api response format
            
            serializer = spoonacularRecipeSerializer(data=raw_data)
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            #if the Api changes and breaks our serializer,return raw data for debugging
            return Response({'error': str(e), 'raw_data': raw_data}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)