from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from .views import SecureLoginView, SecureLogoutView, UserRoleView, CustomRegisterView, NotificationPreferencesView, NotificationViewSet
from rest_framework.routers import DefaultRouter

@method_decorator(ensure_csrf_cookie, name='dispatch')
class GetCSRFToken(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        return HttpResponse()

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('login/', SecureLoginView.as_view(), name='login'),
    path('logout/', SecureLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/role/', UserRoleView.as_view(), name='user_role'),
    path('registration/', CustomRegisterView.as_view(), name='registration'),
    path('csrf/', GetCSRFToken.as_view(), name='csrf'),
    path('notification-preferences/', NotificationPreferencesView.as_view(), name='notification-preferences'),
    path('', include(router.urls)),
]
