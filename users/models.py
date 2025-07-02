from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import TextChoices

# Create your models here.

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    ROLES = (
        ('ADMIN', 'Admin'),
        ('FARMER', 'Farmer'),
        ('STAFF', 'Staff'),
    )
    role = models.CharField(max_length=20, choices=ROLES)
    is_active = models.BooleanField(default=False)
    last_login_ip = models.GenericIPAddressField(null=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True)

    username = None
    email = models.EmailField(_('email address'), unique=True)
    phone_no = models.CharField(_('phone number'), max_length=15, blank=True, null=True)
    first_name = models.CharField(_('first name'), max_length=150, blank=True, null=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    notify_permit_status = models.BooleanField(default=True, help_text='Receive email notifications for permit status changes')
    notify_permit_expiry = models.BooleanField(default=True, help_text='Receive email reminders for permit expiry')
    DIGEST_FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]
    digest_frequency = models.CharField(
        max_length=10,
        choices=DIGEST_FREQUENCY_CHOICES,
        default='weekly',
        help_text='Frequency of summary/digest emails'
    )

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_no']

    def __str__(self):
        return self.email

    def has_role(self, role):
        """
        Role hierarchy implementation:
        - Admin can access everything
        - Staff can access farmer-level features
        - Farmers can only access their own data
        """
        role_hierarchy = {
            'ADMIN': ['ADMIN', 'STAFF', 'FARMER'],
            'STAFF': ['STAFF', 'FARMER'],
            'FARMER': ['FARMER']
        }
        return role in role_hierarchy.get(self.role, [])

    def can_perform_action(self, action_type):
        """
        Check if user can perform specific actions based on their role
        """
        action_permissions = {
            'ADMIN': ['approve_society', 'reject_society', 'view_all_societies'],
            'STAFF': ['view_all_societies'],
            'FARMER': ['manage_own_society']
        }
        return action_type in action_permissions.get(self.role, [])

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

class Notification(models.Model):
    recipient = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=50)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} for {self.recipient.email} at {self.created_at}";
