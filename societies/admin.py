from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Society, Factory, CoffeePrice, AuditLog


@admin.register(Society)
class SocietyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "manager",
        "county",
        "sub_county",
        "is_approved",
        "date_registered",
        "date_approved",
    )
    list_filter = (
        "is_approved",
        "county",
        "sub_county",
        "date_registered",
        "date_approved",
    )
    search_fields = (
        "name",
        "manager__email",
        "manager__first_name",
        "manager__last_name",
        "county",
        "sub_county",
    )
    readonly_fields = (
        "date_registered",
        "date_approved",
        "date_rejected",
    )
    fieldsets = (
        (None, {"fields": ("name", "manager", "county", "sub_county")}),
        (
            _("Approval Status"),
            {
                "fields": (
                    "is_approved",
                    "approved_by",
                    "date_approved",
                    "rejection_reason",
                    "date_rejected",
                    "rejected_by",
                )
            },
        ),
    )


@admin.register(Factory)
class FactoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "society",
        "is_active",
        "county",
        "sub_county",
        "date_added",
        "date_updated",
    )
    list_filter = (
        "is_active",
        "society",
        "county",
        "sub_county",
        "date_added",
        "date_updated",
    )
    search_fields = (
        "name",
        "society__name",
        "county",
        "sub_county",
    )
    readonly_fields = ("date_added", "date_updated")


@admin.register(CoffeePrice)
class CoffeePriceAdmin(admin.ModelAdmin):
    list_display = (
        "society",
        "coffee_grade",
        "coffee_year",
        "price_per_bag",
        "effective_date",
        "is_active",
    )
    list_filter = ("society", "coffee_grade", "coffee_year", "is_active")
    search_fields = ("society__name", "coffee_grade__grade", "coffee_year")
    list_editable = ("price_per_bag", "is_active")
    date_hierarchy = "effective_date"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("society", "coffee_grade")
