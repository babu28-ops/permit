from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SocietyRegistrationView, SocietyViewSet, FactoryViewSet, CoffeePriceViewSet, AdminSocietyViewSet, AdminSocietyRegistrationView, AuditLogListView

router = DefaultRouter()
router.register(r'societies', SocietyViewSet, basename='society')
router.register(r'factories', FactoryViewSet, basename='factory')
router.register(r'coffee-prices', CoffeePriceViewSet, basename='coffee-price')
router.register(r'admin/societies', AdminSocietyViewSet, basename='admin-society')

urlpatterns = [
    path('register/', SocietyRegistrationView.as_view(), name='society-register'),
    path('admin/societies/register/', AdminSocietyRegistrationView.as_view(), name='admin-society-register'),
    path('admin/audit-log/', AuditLogListView.as_view(), name='admin-audit-log'),
    path('', include(router.urls)),
]
