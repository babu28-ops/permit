from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import UserDetailsSerializer, PasswordChangeSerializer
from django.contrib.auth import get_user_model
from societies.serializers import SocietySerializer
import re

User = get_user_model()

class NotificationPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'notify_permit_status',
            'notify_permit_expiry',
            'digest_frequency',
        ]

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user data in permit applications
    """
    full_name = serializers.SerializerMethodField()
    managed_society = SocietySerializer(read_only=True)
    notify_permit_status = serializers.BooleanField()
    notify_permit_expiry = serializers.BooleanField()
    digest_frequency = serializers.CharField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone_no',
            'role', 'full_name', 'managed_society',
            'notify_permit_status', 'notify_permit_expiry', 'digest_frequency',
        ]
        read_only_fields = ['id', 'email', 'role']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email

class CustomUserDetailsSerializer(UserDetailsSerializer):
    """
    Extended user details serializer for authentication
    """
    full_name = serializers.SerializerMethodField()
    managed_society = SocietySerializer(read_only=True)
    notify_permit_status = serializers.BooleanField()
    notify_permit_expiry = serializers.BooleanField()
    digest_frequency = serializers.CharField()
    
    class Meta(UserDetailsSerializer.Meta):
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'phone_no',
            'is_staff', 'is_superuser', 'role', 'full_name',
            'managed_society',
            'notify_permit_status', 'notify_permit_expiry', 'digest_frequency',
        )
        read_only_fields = ('email', 'role')

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email

class CustomRegisterSerializer(RegisterSerializer):
    """
    Custom registration serializer
    """
    username = None  # Remove username field
    email = serializers.EmailField(required=True)
    phone_no = serializers.CharField(required=True, max_length=15)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate_phone_no(self, value):
        if User.objects.filter(phone_no=value).exists():
            raise serializers.ValidationError(
                "A user with this phone number already exists."
            )
        return value

    def get_cleaned_data(self):
        return {
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'phone_no': self.validated_data.get('phone_no', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
        }

    def save(self, request):
        try:
            user = super().save(request)
            user.phone_no = self.cleaned_data.get('phone_no')
            user.first_name = self.cleaned_data.get('first_name')
            user.last_name = self.cleaned_data.get('last_name')
            user.save()
            return user
        except Exception as e:
            raise serializers.ValidationError(f"Error saving user: {str(e)}")

class LoginSerializer(serializers.Serializer):
    login_field = serializers.CharField()
    password = serializers.CharField()

    def validate_login_field(self, value):
        if '@' in value:
            # Validate email
            if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
                raise serializers.ValidationError("Invalid email format.")
        else:
            # Validate phone (example: 10 digits)
            if not re.match(r"^[0-9]{10}$", value):
                raise serializers.ValidationError("Invalid phone number format.")
        return value

class CustomPasswordChangeSerializer(PasswordChangeSerializer):
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            # Use a generic error message
            raise serializers.ValidationError("Unable to change password. Please check your credentials and try again.")
        return value

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User.notifications.rel.related_model
        fields = ['id', 'type', 'message', 'is_read', 'created_at', 'link']