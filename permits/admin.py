from django.contrib import admin
from .models import PermitApplication, CoffeeQuantity, CoffeeGrade
from django.utils.html import format_html
from django.db.models import Sum
from django.utils import timezone


class CoffeeQuantityInline(admin.TabularInline):
    model = CoffeeQuantity
    extra = 1
    fields = ("coffee_grade", "bags_quantity", "total_weight")
    readonly_fields = ("total_weight",)


@admin.register(CoffeeGrade)
class CoffeeGradeAdmin(admin.ModelAdmin):
    list_display = ("grade", "weight_per_bag", "description", "created_at", "updated_at")
    search_fields = ("grade",)
    list_filter = ("grade",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(PermitApplication)
class PermitApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "ref_no",
        "farmer",
        "society",
        "factory",
        "warehouse",
        "application_date",
        "delivery_start",
        "delivery_end",
        "status",
        "total_bags",
        "total_weight",
        "is_valid_display",
        "is_expired_display",
    )
    list_filter = (
        "status",
        "application_date",
        "delivery_start",
        "delivery_end",
        "society",
        "factory",
        "warehouse",
    )
    search_fields = (
        "ref_no",
        "farmer__username",
        "farmer__email",
        "society__name",
        "factory__name",
        "warehouse__name",
    )
    readonly_fields = (
        "ref_no",
        "application_date",
        "approved_at",
        "rejected_at",
        "total_bags",
        "total_weight",
        "is_valid",
        "is_expired",
    )
    inlines = [CoffeeQuantityInline]
    actions = ['bulk_approve', 'bulk_reject', 'bulk_cancel']

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("ref_no", "farmer", "application_date", "status")},
        ),
        ("Location Details", {"fields": ("society", "factory", "warehouse")}),
        ("Delivery Period", {"fields": ("delivery_start", "delivery_end")}),
        (
            "Approval Details",
            {
                "fields": (
                    "approved_by",
                    "approved_at",
                    "rejected_by",
                    "rejected_at",
                    "rejection_reason"
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Summary",
            {
                "fields": (
                    "total_bags",
                    "total_weight",
                    "is_valid",
                    "is_expired"
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def is_valid_display(self, obj):
        if obj.is_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Invalid</span>')
    is_valid_display.short_description = "Valid"

    def is_expired_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">✗ Expired</span>')
        return format_html('<span style="color: green;">✓ Active</span>')
    is_expired_display.short_description = "Expired"

    def total_bags(self, obj):
        return obj.total_bags
    total_bags.short_description = "Total Bags"

    def total_weight(self, obj):
        return f"{obj.total_weight} kg"
    total_weight.short_description = "Total Weight"

    def bulk_approve(self, request, queryset):
        if not request.user.is_staff:
            self.message_user(request, "Only staff members can approve permits.", level='error')
            return
        
        current_time = timezone.now()
        for permit in queryset.filter(status='PENDING'):
            permit.status = 'APPROVED'
            permit.approved_by = request.user
            permit.approved_at = current_time
            permit.save()
        
        self.message_user(request, f"Successfully approved {queryset.count()} permits.")
    bulk_approve.short_description = "Approve selected permits"

    def bulk_reject(self, request, queryset):
        if not request.user.is_staff:
            self.message_user(request, "Only staff members can reject permits.", level='error')
            return
        
        for permit in queryset.filter(status='PENDING'):
            permit.status = 'REJECTED'
            permit.rejected_by = request.user
            permit.rejected_at = timezone.now()
            permit.rejection_reason = "Rejected via admin interface"
            permit.save()
        
        self.message_user(request, f"Successfully rejected {queryset.count()} permits.")
    bulk_reject.short_description = "Reject selected permits"

    def bulk_cancel(self, request, queryset):
        for permit in queryset.filter(status__in=['PENDING', 'APPROVED']):
            permit.status = 'CANCELLED'
            permit.save()
        
        self.message_user(request, f"Successfully cancelled {queryset.count()} permits.")
    bulk_cancel.short_description = "Cancel selected permits"


@admin.register(CoffeeQuantity)
class CoffeeQuantityAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "coffee_grade",
        "bags_quantity",
        "total_weight",
        "application_status"
    )
    list_filter = ("coffee_grade", "application__status")
    search_fields = (
        "application__ref_no",
        "coffee_grade__grade",
        "application__farmer__email"
    )
    readonly_fields = ("total_weight", "application_status")

    def application_status(self, obj):
        status_colors = {
            'PENDING': 'orange',
            'APPROVED': 'green',
            'REJECTED': 'red',
            'CANCELLED': 'gray',
            'EXPIRED': 'red'
        }
        color = status_colors.get(obj.application.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.application.status
        )
    application_status.short_description = "Permit Status"
