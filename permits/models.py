from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta
from django.db import transaction
from django.core.exceptions import ValidationError

from users.models import CustomUser
from societies.models import CoffeePrice
import decimal


class CoffeeGrade(models.Model):
    grade = models.CharField(
        max_length=30,
        unique=True,
    )
    weight_per_bag = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Weight in kilograms per bag"
    )
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    def __str__(self):
        return f"{self.grade} ({self.weight_per_bag}kg)"


class PermitApplication(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"),
    ]

    ref_no = models.CharField(max_length=20, editable=False)
    farmer = models.ForeignKey(
        CustomUser, on_delete=models.PROTECT, related_name="applications"
    )
    society = models.ForeignKey(
        'societies.Society',  # Use string reference with app name
        on_delete=models.PROTECT,
        related_name="permits"
    )
    factory = models.ForeignKey(
        'societies.Factory',  # Use string reference with app name
        on_delete=models.PROTECT,
        related_name="permits"
    )
    warehouse = models.ForeignKey(
        'warehouse.Warehouse',  # Use string reference with app name
        on_delete=models.PROTECT,
        related_name="permits"
    )
    application_date = models.DateTimeField(auto_now_add=True)
    delivery_start = models.DateField(null=True, blank=True)
    delivery_end = models.DateField(null=True, blank=True)

    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_permits",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rejected_permits",
    )
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    def save(self, *args, **kwargs):
        # Generate ref_no only if it's a new permit and status is being changed to APPROVED/REJECTED
        if (self.status in ["APPROVED", "REJECTED"]) and not self.ref_no:
            # Determine the coffee year
            current_date = timezone.now().date()
            current_year = current_date.year

            if current_date.month < 10:
                coffee_year_start = current_year - 1
                coffee_year_end = current_year
            else:
                coffee_year_start = current_year
                coffee_year_end = current_year + 1

            distribution_year = f"{coffee_year_start}/{str(coffee_year_end)[-2:]}"

            last_permit = (
                PermitApplication.objects.filter(
                    ref_no__startswith=f"MCG-CD/{distribution_year}"
                )
                .order_by("-ref_no")
                .first()
            )

            if last_permit:
                try:
                    last_number = int(last_permit.ref_no.split("MP")[-1].strip())
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1

            self.ref_no = f"MCG-CD/{distribution_year} MP {new_number:03d}"

        # Handle delivery dates based on status changes
        if self.pk:
            original = PermitApplication.objects.get(pk=self.pk)
            if original.status != self.status:
                if self.status == "APPROVED":
                    self.delivery_start = timezone.now().date()
                    self.delivery_end = self.delivery_start + timedelta(days=7)
                elif self.status == "REJECTED":
                    self.delivery_start = None
                    self.delivery_end = None
        
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        return (
            self.status == "APPROVED"
            and self.delivery_start
            and self.delivery_end
            and self.delivery_start <= timezone.now().date() <= self.delivery_end
        )

    def check_expiration(self):
        if (
            self.status == "APPROVED"
            and self.delivery_end
            and timezone.now().date() > self.delivery_end
        ):
            self.status = "EXPIRED"
            self.save()

    @property
    def total_bags(self):
        """Calculate total number of bags across all coffee grades"""
        return (
            self.coffee_quantities.aggregate(total=models.Sum("bags_quantity"))["total"]
            or 0
        )

    @property
    def total_weight(self):
        """Calculate total weight across all coffee grades"""
        total = 0
        for quantity in self.coffee_quantities.all():
            # Ensure the related coffee_grade is fetched
            if hasattr(quantity, 'coffee_grade') and quantity.coffee_grade:
                weight_per_bag = float(quantity.coffee_grade.weight_per_bag)
                total += quantity.bags_quantity * weight_per_bag
        return total

    def update_status(self):
        """Update permit status based on delivery end date"""
        if self.status == "APPROVED" and self.delivery_end and timezone.now().date() > self.delivery_end:
            self.status = "EXPIRED"
            self.save()
        return self.status

    @property
    def is_expired(self):
        """Check if permit is expired"""
        return self.status == "APPROVED" and self.delivery_end and timezone.now().date() > self.delivery_end

    def __str__(self):
        ref = self.ref_no if self.ref_no else "Pending"
        return f"Permit {ref} - {self.farmer}"

    @transaction.atomic
    def approve(self, approved_by):
        if self.status != "PENDING":
            raise ValidationError("Only pending permits can be approved")

        self.status = "APPROVED"
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.save()


@receiver(post_save, sender=PermitApplication)
def check_permit_expiration(sender, instance, **kwargs):
    instance.check_expiration()


class CoffeeQuantity(models.Model):
    application = models.ForeignKey(
        PermitApplication, on_delete=models.PROTECT, related_name="coffee_quantities"
    )
    coffee_grade = models.ForeignKey(
        'permits.CoffeeGrade', on_delete=models.PROTECT, related_name="permit_quantities" # Ensure string reference here too
    )
    bags_quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = ["application", "coffee_grade"]
        verbose_name_plural = "Coffee Quantities"

    def __str__(self):
        return f"{self.bags_quantity} bags of {self.coffee_grade} for {self.application.ref_no}"

    @property
    def total_weight(self):
        """Calculate total weight for this specific coffee grade"""
        return self.bags_quantity * float(self.coffee_grade.weight_per_bag)
