from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/auth/", include("dj_rest_auth.urls")),
    path("api/auth/", include("django.contrib.auth.urls")),
    path("api/societies/", include("societies.urls")),
    path("api/warehouse/", include("warehouse.urls")),
    path("api/permits/", include("permits.urls")),
    path("accounts/", include("allauth.urls")),
]

# Serve static files only in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
