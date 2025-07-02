"""
ASGI config for server project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
import django
from django.core.asgi import get_asgi_application

# Set the default Django settings module before any imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()  # This is the key line that was missing

# Now import other ASGI components
from channels.routing import ProtocolTypeRouter, URLRouter
from users.jwt_channels_middleware import JWTAuthMiddleware
import users.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(
            users.routing.websocket_urlpatterns
        )
    ),
})