from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
#Your Custom user model is the actual foundation of identity for your end users
#call it an IDENTITY CARD for end users and should contain all the infor about end users can input
from django.contrib.auth.models import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    #replace username with email as the unique identifier
    username = None
    email = models.EmailField(_("email address"), unique=True)# simpleJWT is easily configured to allow logins with emails
    name = models.CharField(max_length=255, blank=True)
    bio=models.TextField(max_length=500,blank=True)
    profile_picture=models.ImageField(upload_to='profile_pics/',blank=True,null=True)
#link the manager to the custom user model
#the manager will handle password hashing and email normalization,when creating users
    objects = UserManager()
    #identify email as the unique identifier for authentication instead of username
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    #custom Roles,also when you add a chef-only feature in future this field will be available
    is_chef=models.BooleanField(default=False)# users can't just claim to chefs unless verified by you in admin panel

    #Audit timestamps
    updated_at=models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.email
    # i still need to add signals.py file for broadcast welcome email on user registration
