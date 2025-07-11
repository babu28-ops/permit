from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from decouple import config

class Command(BaseCommand):
    help = 'Creates a new admin user using credentials from .env file'

    def handle(self, *args, **options):
        User = get_user_model()
        email = config("DEFAULT_ADMIN_EMAIL")
        password = config("DEFAULT_ADMIN_PASSWORD")

        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError(f'Error: Invalid email format: {email}')

        # Check if user with this email already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Admin user with email {email} already exists.'))
            return

        try:
            # Create the user with the ADMIN role
            user = User.objects.create_user(
                email=email,
                password=password,
                role='ADMIN', 
                is_staff=True,
                is_superuser=True,
                is_active=True,
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created admin user: {user.email}'))
        except Exception as e:
            raise CommandError(f'Error creating admin user: {e}')