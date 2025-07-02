from django.contrib import admin
from .models import Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "county",
        "sub_county",
        "licence_number",
        "is_active",
        "date_created",
    )
    list_filter = ("is_active", "county", "sub_county")
    search_fields = ("name", "licence_number", "county", "sub_county")
    readonly_fields = ("date_created", "date_updated", "created_by", "updated_by")
