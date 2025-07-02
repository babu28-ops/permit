from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'coffee-grades', views.CoffeeGradeViewSet)
router.register(r'permits', views.PermitApplicationViewSet)
router.register(r'coffee-quantities', views.CoffeeQuantityViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('permits/<int:permit_id>/pdf/', views.generate_permit_pdf, name='permit_pdf'),
    path('analytics-report-pdf/', views.analytics_report_pdf, name='analytics_report_pdf'),
]
