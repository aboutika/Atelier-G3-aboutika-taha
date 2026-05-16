from django.shortcuts import redirect
from django.contrib import messages
from .models import SiteVisit
from django.contrib.auth import logout
from django.urls import reverse

class SiteVisitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check if user is suspended
            if getattr(request.user, 'is_suspended', False):
                logout(request)
                messages.error(request, "Votre compte a été suspendu par l'administration.")
                return redirect('login')
            
            if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
                SiteVisit.objects.create(
                    user=request.user,
                    path=request.path,
                    ip_address=request.META.get('REMOTE_ADDR')
                )
        response = self.get_response(request)
        return response
