from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from rest_framework import status, viewsets, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework.throttling import AnonRateThrottle
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .serializers import (
    CustomUserDetailsSerializer, LoginSerializer, NotificationPreferencesSerializer, NotificationSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)
from dj_rest_auth.registration.views import RegisterView
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.conf import settings
from django.utils import timezone
from .models import Notification, PasswordResetToken
from django.http import JsonResponse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
import secrets

User = get_user_model()

class LoginRateThrottle(AnonRateThrottle):
    rate = '5/minute'

class TokenRefreshRateThrottle(AnonRateThrottle):
    rate = '10/minute'

class LogoutRateThrottle(AnonRateThrottle):
    rate = '10/minute'

@method_decorator(csrf_protect, name='dispatch')
class SecureLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': 'Invalid credentials.'}, status=400)
        login_field = serializer.validated_data['login_field']
        password = serializer.validated_data['password']

        user = None
        try:
            user = User.objects.get(email=login_field) if '@' in login_field else User.objects.get(phone_no=login_field)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Account lockout check
        if user.account_locked_until and user.account_locked_until > timezone.now():
            return Response({'error': 'Account is temporarily locked due to multiple failed login attempts. Please try again later.'}, status=status.HTTP_403_FORBIDDEN)

        if not user.check_password(password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= getattr(settings, 'MAX_FAILED_ATTEMPTS', 5):
                user.account_locked_until = timezone.now() + timezone.timedelta(minutes=getattr(settings, 'ACCOUNT_LOCKOUT_DURATION', 30))
            user.save(update_fields=['failed_login_attempts', 'account_locked_until'])
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Reset failed attempts on successful login
        if user.failed_login_attempts > 0 or user.account_locked_until:
            user.failed_login_attempts = 0
            user.account_locked_until = None
            user.save(update_fields=['failed_login_attempts', 'account_locked_until'])

        # Check if user is active and approved
        if not user.is_active:
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        user_data = CustomUserDetailsSerializer(user).data
        response = Response({'user': user_data})
        # Set secure, HTTP-only cookies
        response.set_cookie(
            'access_token',
            str(refresh.access_token),
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            max_age=86400 
        )
        response.set_cookie(
            'refresh_token',
            str(refresh),
            httponly=True,
            secure=settings.SESSION_COOKIE_SECURE,
            samesite=settings.SESSION_COOKIE_SAMESITE,
            max_age=432000  
        )
        return response

@method_decorator(csrf_protect, name='dispatch')
class SecureLogoutView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LogoutRateThrottle]

    def post(self, request):
        response = Response({'message': 'Successfully logged out'})
        response.delete_cookie('access_token', path='/', domain=None)
        response.delete_cookie('refresh_token', path='/', domain=None)
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception as e:
            pass
        return response

class UserRoleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'role': request.user.role,
            'is_admin': request.user.role == "ADMIN",
            'is_user': request.user.role == "FARMER",
        })

class CustomRegisterView(RegisterView):
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        # Always return generic error to prevent user enumeration
        try:
            response = super().create(request, *args, **kwargs)
            return response
        except ValidationError as e:
            return Response(
                {'error': 'Registration failed. Please check your details and try again.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'An error occurred during registration. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(csrf_protect, name='dispatch')
class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [TokenRefreshRateThrottle]

    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({'error': 'No refresh token'}, status=400)
        try:
            token = RefreshToken(refresh_token)
            user = token.get('user_id')
            new_refresh = RefreshToken.for_user(user)
            new_access = new_refresh.access_token
            token.blacklist()
            response = Response({'message': 'Token refreshed'})
            response.set_cookie(
                'access_token',
                str(new_access),
                httponly=True,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite=settings.SESSION_COOKIE_SAMESITE,
                max_age=900
            )
            response.set_cookie(
                'refresh_token',
                str(new_refresh),
                httponly=True,
                secure=settings.SESSION_COOKIE_SECURE,
                samesite=settings.SESSION_COOKIE_SAMESITE,
                max_age=86400
            )
            return response
        except (TokenError, InvalidToken) as e:
            return Response({'error': 'Invalid or blacklisted token'}, status=401)

class NotificationPreferencesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = NotificationPreferencesSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = NotificationPreferencesSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def get_object(self):
        obj = super().get_object()
        if obj.recipient != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to access this notification.")
        return obj

    def partial_update(self, request, *args, **kwargs):
        # Only allow marking as read
        instance = self.get_object()
        if 'is_read' in request.data:
            instance.is_read = request.data.get('is_read', True)
            instance.save(update_fields=['is_read'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

@method_decorator(ensure_csrf_cookie, name='dispatch')
class GetCSRFToken(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        from django.middleware.csrf import get_token
        token = get_token(request)
        return JsonResponse({'csrfToken': token})

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Always return success to prevent user enumeration
            return Response({'message': 'If an account with that email exists, a reset link has been sent.'})
        # Invalidate previous tokens
        PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
        # Generate token
        token = secrets.token_urlsafe(32)
        expiry = timezone.now() + timezone.timedelta(days=3)
        reset_token = PasswordResetToken.objects.create(user=user, token=token, expiry=expiry)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"{settings.CLIENT_URL}/reset-password/{uidb64}/{token}"
        # Send email
        context = {
            'first_name': user.first_name or user.email,
            'reset_link': reset_link,
            'admin_name': getattr(settings, 'ADMIN_USER_NAME', 'Admin'),
        }
        subject = 'Password Reset Request'
        message = render_to_string('emails/password_reset_custom.html', context)
        send_mail(
            subject,
            '',
            settings.EMAIL_HOST_USER,
            [user.email],
            html_message=message,
        )
        return Response({'message': 'If an account with that email exists, a reset link has been sent.'})

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uidb64 = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password1']
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            User = get_user_model()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid link.'}, status=400)
        try:
            reset_token = PasswordResetToken.objects.get(user=user, token=token, used=False)
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid or expired token.'}, status=400)
        if not reset_token.is_valid():
            return Response({'error': 'Token expired or already used.'}, status=400)
        # Set new password
        user.set_password(new_password)
        user.save()
        reset_token.mark_used()
        return Response({'message': 'Password reset successful.'})
