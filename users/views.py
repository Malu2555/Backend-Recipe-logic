from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, decorators, response, status

from .serializers import UserSerializer, UserCreateSerializer, PasswordSerializer
from .permissions import IsAdminOrSelf
#handle the XSS-SAFE cookie logic here,
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.response import Response    
from django.conf import settings

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        #1. get  the standard response(which includes the access and refresh tokens)frpm parent class
        response = super().post(request, *args, **kwargs)
        #remember to include  the platform flag  in your vue.js login request payload, e.g., {username: "user1", password: "pass123", platform: "web"}
        if request.data.get("platform") == "web":#2. check if the login request is coming from the web platform
            # Set the access token in an HttpOnly cookie
            access_token = response.data.get('access')
            refresh_token = response.data.get('refresh')
            if access_token and refresh_token:
                # Set the access token in an HttpOnly cookie
                response.set_cookie(
                    key=settings.SIMPLE_JWT['AUTH_COOKIE'],  # Use the same name as defined in settings
                    value=refresh_token,
                    httponly=True,# js can't access the cookie, helps prevent XSS attacks
                    secure=settings.SIMPLE_JWT['AUTH_COOKIE_SECURE'],
                    samesite=settings.SIMPLE_JWT['AUTH_COOKIE_SAMESITE']
                )
            
                del response.data['refresh']  # Remove refresh token from response body for security
        return response
#make sure the tokenrefreshView also checks for the platform flag and sets the cookie accordingly when refreshing tokens,so that the web client can maintain the session seamlessly without needing to handle tokens in JavaScript.
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        #if the refresh token is missingfrom the request body,check if it's available in the cookie (for web clients)
        refresh_token=request.data.get('refresh') or request.COOKIES.get(settings.SIMPLE_JWT['AUTH_COOKIE'])
        if refresh_token:
            #inject the refresh token back into the request data so that the parent class can process it correctly
            request.data['refresh'] = refresh_token
            response = super().post(request, *args, **kwargs)
    

User = get_user_model()

#listing,retrieving,creating,updating,deleting users handled here,done by an admin
class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing users."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
#dynamic serializer selection based on action
#1. Map Registration to 'create'(POST/ users/)
    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer #serializer for creating new users
        if self.action == "set_password":
            return PasswordSerializer#2.serializer for changing user passwords
        return UserSerializer#3. default for list(GET/users/) and retrieve(GET/users/1/)
#here you are defining how to get the permissions from permissions.py,you are not creating the actual permissions
#the permissions here are references from both the recipes's permissions.py and user's permissions.py
    def get_permissions(self):
        if self.action == "create":
            return [permissions.AllowAny()]# anybody can create data
        if self.action in ["list", "destroy"]:
            return [permissions.IsAdminUser()]# only admin can list or destroy/a user should be able to delete their acc
        if self.action in ["retrieve", "update", "partial_update", "me", "set_password"]:
            return [permissions.IsAuthenticated(), IsAdminOrSelf()]# admin or logged-in user themselves

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return response.Response(serializer.data)

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def set_password(self, request):
        serializer = PasswordSerializer(data=request.data)
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data["new_password"])
            request.user.save()
            return response.Response(status=status.HTTP_204_NO_CONTENT)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    #note that it is a single viewset handling everything
#handle logout by creating  a separate view
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # Get  the refresh token from JSON for mobile clients or from the cookie for web clients
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()#blacklist the refresh token from the db to prevent further use
            response = Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
            # Clear the access token cookie
            response.delete_cookie(settings.SIMPLE_JWT['AUTH_COOKIE'])
            return response
        except Exception as e:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

