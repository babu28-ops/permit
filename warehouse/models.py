from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    county = models.CharField(max_length=100)
    sub_county = models.CharField(max_length=100)
    licence_number = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_warehouses",
    )
    updated_by = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.SET_NULL,
        null=True,
        related_name="updated_warehouses",
)

    class Meta:
        ordering = ["-date_created"]
        verbose_name = "Warehouse"
        verbose_name_plural = "Warehouses"

    def __str__(self):
        return f"{self.name} - {self.licence_number}"
