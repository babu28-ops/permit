from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from users.models import CustomUser # Import your CustomUser model directly
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

class Command(BaseCommand):
    help = 'Creates a new user with the "ADMIN" role.'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='The email for the new admin user.')
        parser.add_argument('password', type=str, help='The password for the new admin user.')

    def handle(self, *args, **options):
        User = get_user_model()
        email = options['email']
        password = options['password']

        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError(f'Error: Invalid email format: {email}')

        # Check if user with this email already exists
        if User.objects.filter(email=email).exists():
            raise CommandError(f'Error: User with email {email} already exists.')

        try:
            # Create the user with the ADMIN role
            # Ensure is_staff and is_superuser are also True for admin role
            user = User.objects.create_user(
                email=email,
                password=password,
                role=CustomUser.Role.ADMIN, # Assign the ADMIN role
                is_staff=True,             # Admins should generally be staff
                is_superuser=True,         # Admins should generally be superusers
                is_active=True,            # Make the admin account active
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created admin user: {user.email}'))
        except Exception as e:
            raise CommandError(f'Error creating admin user: {e}')
