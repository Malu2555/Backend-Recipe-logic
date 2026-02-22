from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import gettext_lazy as _# utility for language translation,eng to swa etc

from .models import User
'''for a customuser in admin,we need to define custom forms for user creation and user change,
then create a custom UserAdmin class to use these forms and register it with the admin site
since right now the admin panel won't recognize our custom user model,
ONLY FOR YOU AND YOUR TEAM'''
class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes a repeated password field."""
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Password confirmation", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "name")
# a method to validate that the two password entries match
    def clean_password2(self):
        p1 = self.cleaned_data.get("password1")
        p2 = self.cleaned_data.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords don't match")
        return p2
# a method to save the provided password in hashed format
    def save(self, commit=True):
        user = super().save(commit=False)#commit false to avoid saving yet
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()#save the user password to the database?
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Replaces the password field with admin's readonly field."""
    password = ReadOnlyPasswordHashField()# only display the hashed password

    class Meta:
        model = User
    
        fields = ("email", "name", "password", "is_active", "is_staff")

    def clean_password(self):
        return self.initial.get("password")

# An admin class that is going to use the above forms in the admin panel,a custom admin class
class UserAdmin(DjangoUserAdmin):
    form = UserChangeForm # create new users form
    add_form = UserCreationForm #update users form

# controls the layout of the change for an existing user
    fieldsets = (
        (None, {"fields": ("email", "password")} ),
        (_("Personal info"), {"fields": ("name",)}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")} ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")} ),
    )
#controls the layout of the add page(creation) for a new user
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2"),
        }),
    )
# list_display controls what is to be seen on the admin panel
    list_display = ("email", "name", "is_staff", "is_active")
    search_fields = ("email", "name")
    ordering = ("email",)


admin.site.register(User, UserAdmin)
#create a superuser using the command: python manage.py createsuperuser on 3rd december 2026

