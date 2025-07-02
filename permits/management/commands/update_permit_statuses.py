from django.core.management.base import BaseCommand
from django.utils import timezone
from permits.models import PermitApplication

class Command(BaseCommand):
    help = 'Updates permit statuses based on delivery end dates'

    def handle(self, *args, **options):
        # Get all approved permits
        approved_permits = PermitApplication.objects.filter(status='APPROVED')
        updated_count = 0

        for permit in approved_permits:
            if permit.is_expired:
                permit.status = 'EXPIRED'
                permit.save()
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Updated permit {permit.ref_no} status to EXPIRED'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated {updated_count} permits to EXPIRED status'
            )
        )
