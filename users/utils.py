from .models import CustomUser, Notification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from users.serializers import NotificationSerializer

def notify_users(users, type, message, link=None):
    """
    Send a notification to one or more users.
    users: a user instance or a list/queryset of users
    """
    from collections.abc import Iterable
    channel_layer = get_channel_layer()
    if not isinstance(users, Iterable) or isinstance(users, str):
        users = [users]
    for user in users:
        notif = Notification.objects.create(
            recipient=user,
            type=type,
            message=message,
            link=link or ''
        )
        # Send real-time notification
        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}",
            {
                "type": "notify",
                "content": NotificationSerializer(notif).data,
            }
        )

# Backward compatible aliases
notify_user = notify_users

def notify_admins(type, message, link=None):
    admins = CustomUser.objects.filter(is_staff=True, is_active=True)
    notify_users(admins, type, message, link) 