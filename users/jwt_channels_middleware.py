from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

@database_sync_to_async
def get_user(validated_token):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user_id = validated_token['user_id']
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTAuthMiddleware:
    """
    Custom middleware that takes a JWT from the cookies and authenticates via Channels.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Only handle websocket connections
        if scope["type"] != "websocket":
            return await self.app(scope, receive, send)

        headers = dict(scope.get("headers", {}))
        cookies = {}
        
        # Parse cookies from headers
        if b'cookie' in headers:
            from http.cookies import SimpleCookie
            cookie = SimpleCookie()
            cookie.load(headers[b'cookie'].decode())
            cookies = {k: v.value for k, v in cookie.items()}

        access_token = cookies.get('access_token')
        scope['user'] = AnonymousUser()

        if access_token:
            try:
                validated_token = UntypedToken(access_token)
                scope['user'] = await get_user(validated_token)
            except (InvalidToken, TokenError) as e:
                pass

        return await self.app(scope, receive, send)