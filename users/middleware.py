#for implementing is_blocked check as a global middle so you do not have to
#add decorators to every view,remember to add it in settings.py's middleware
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class BlockedUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        #1.check if user is logged in and BLOCKED
        if request.user.is_authenticated and getattr(request.user, 'is_blocked', False):
        #2. allow them(blocked users) to access the logout page(avoid getting stuck forever)
        #-and the 'blocked' infor page if you choose to have one in the frontend
           allowed_urls=[reverse('logout'), reverse('blocked_infor')]
           if request.path not in allowed_urls:
               messages.error(request,"Your account is currently suspended.")
               #This returns a Redirect Object(which has a status_code-normally)
               return redirect('blocked_infor')
           #if they are not blocked,we must call the next middleware
           #and return that response object as below
        response=self.get_response(request)
           #you will get a "NoneType" error if you miss this return
        return response
        # add the users.middleware.BlockedUserMiddleware in your Middleware config
        #and then you can run your migrations and create your cache table(if you have't yet)