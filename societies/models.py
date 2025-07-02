from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from users.models import CustomUser

class Society(models.Model):
    name = models.CharField(_('society name'), max_length=255, unique=True)
    manager = models.OneToOneField(
        CustomUser,
        on_delete=models.PROTECT,
        related_name='managed_society'
    )
    county = models.CharField(_('county'), max_length=100)
    sub_county = models.CharField(_('sub county'), max_length=100)
    is_approved = models.BooleanField(default=False)
    date_registered = models.DateTimeField(auto_now_add=True)
    date_approved = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='approved_societies'
    )
    rejection_reason = models.TextField(_('rejection reason'), null=True, blank=True)
    date_rejected = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='rejected_societies'
    )

    def __str__(self):
        return self.name

class Factory(models.Model):
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='factories'
    )
    name = models.CharField(_('factory name'), max_length=255)
    is_active = models.BooleanField(default=True)
    county = models.CharField(_('county'), max_length=100, blank=True, null=True)
    sub_county = models.CharField(_('sub county'), max_length=100, blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.society.name}"

class CoffeePrice(models.Model):
    society = models.ForeignKey(
        Society,
        on_delete=models.CASCADE,
        related_name='coffee_prices'
    )
    coffee_grade = models.ForeignKey(
        'permits.CoffeeGrade',
        on_delete=models.PROTECT,
        related_name='prices',
        verbose_name=_('coffee grade')
    )
    coffee_year = models.CharField(
        _('coffee year'),
        max_length=9,  # Format: "2023/24"
        help_text="Coffee year in format YYYY/YY"
    )
    price_per_bag = models.DecimalField(
        _('price per bag'),
        max_digits=10,
        decimal_places=2
    )
    effective_date = models.DateField()
    is_active = models.BooleanField(default=True)
    date_set = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['society', 'coffee_grade', 'coffee_year']
        ordering = ['-coffee_year', '-effective_date']

    def __str__(self):
        return f"{self.society.name} - {self.coffee_grade.grade} - {self.coffee_year} - {self.price_per_bag}"

    def clean(self):
        # Validate coffee year format
        import re
        if not re.match(r'^\d{4}/\d{2}$', self.coffee_year):
            raise ValidationError(_('Coffee year must be in format YYYY/YY (e.g., 2023/24)'))

    @classmethod
    def get_current_coffee_year(cls):
        """Get the current coffee year based on the current date"""
        current_date = timezone.now().date()
        if current_date.month < 10:
            return f"{current_date.year - 1}/{str(current_date.year)[-2:]}"
        return f"{current_date.year}/{str(current_date.year + 1)[-2:]}"

    @property
    def is_currently_active(self):
        return self.effective_date <= timezone.now().date()

class AuditLog(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    model = models.CharField(max_length=255)
    object_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(null=True)
    details = models.JSONField(null=True)

    class Meta:
        ordering = ['-timestamp']
