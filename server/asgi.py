import os
from django.core.asgi import get_asgi_application

# Set default settings first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')

# Get ASGI application
django_application = get_asgi_application()

# Now import other components
from channels.routing import ProtocolTypeRouter, URLRouter
from users.jwt_channels_middleware import JWTAuthMiddleware
import users.routing

application = ProtocolTypeRouter({
    "http": django_application,
    "websocket": JWTAuthMiddleware(
        URLRouter(
            users.routing.websocket_urlpatterns
        )
    ),
})