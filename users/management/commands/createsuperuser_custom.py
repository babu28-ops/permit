from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser with email, phone, and national_id'

    def handle(self, *args, **options):
        try:
            email = input('Enter email: ')
            phone = input('Enter phone number: ')
            national_id = input('Enter national ID: ')
            password = input('Enter password: ')
            password2 = input('Confirm password: ')

            if password != password2:
                self.stdout.write(self.style.ERROR('Passwords do not match!'))
                return

            user = User.objects.create_superuser(
                email=email,
                phone=phone,
                national_id=national_id,
                password=password
            )

            self.stdout.write(self.style.SUCCESS(f'Superuser {email} created successfully!'))
            
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))
