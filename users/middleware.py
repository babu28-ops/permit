from django.middleware.csrf import get_token
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from django.conf import settings
from rest_framework.authtoken.models import Token as AccessToken
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status

class CsrfTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Set CSRF token for authenticated users
        if request.user.is_authenticated:
            response['X-CSRF-Token'] = get_token(request)
        return response 

class SecurityMiddleware:
    """
    Middleware to handle security checks:
    - Account lockout after failed attempts
    - IP address tracking
    - Suspicious activity detection
    - Session management
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Check for account lockout
            if request.user.account_locked_until and request.user.account_locked_until > timezone.now():
                raise PermissionDenied("Account is locked. Try again later.")

            # Track IP changes
            current_ip = request.META.get('REMOTE_ADDR')
            if request.user.last_login_ip and request.user.last_login_ip != current_ip:
                request.user.last_login_ip = current_ip
                request.user.save()

            # Check for suspicious activity
            if self._is_suspicious_activity(request):
                request.user.failed_login_attempts += 1
                if request.user.failed_login_attempts >= settings.MAX_FAILED_ATTEMPTS:
                    request.user.account_locked_until = timezone.now() + timezone.timedelta(minutes=30)
                request.user.save()

        response = self.get_response(request)
        return response

    def _is_suspicious_activity(self, request):
        # Implement your suspicious activity detection logic here
        return False 

class TokenValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Removed custom token validation logic for security and reliability
        return self.get_response(request) 