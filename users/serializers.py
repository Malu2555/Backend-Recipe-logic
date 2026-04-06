from django.contrib.auth import get_user_model
from rest_framework import serializers
#serializers are the actual end user "input forms" just like you did in admin.py for staff
User = get_user_model()
#all of the serializers related to the User model
#they validate and transform data for user-related operations

# user serializer for listing and retrieving user details
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "name", "is_staff","bio","is_superuser")
        read_only_fields = ("id", "is_staff","is_superuser")

# user serializer for creating new users
class UserCreateSerializer(serializers.ModelSerializer):# this is your user registration serializer
    password = serializers.CharField(write_only=True, min_length=16)

    class Meta:
        model = User
        fields = ("id", "email", "name", "password")
        read_only_fields = ("id",)
#the modelserializer's create method is overridden to handle password hashing
    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

#validator and transformer for changing user passwords
class PasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(min_length=8)
#remember should handle user logins by using SimpleJWT tokens
#your user serializer thus handles automatic user registration by end users.
