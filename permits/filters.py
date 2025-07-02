from django_filters import rest_framework as filters
from .models import PermitApplication
from django.db.models import Sum, F, FloatField, Q
from django.utils import timezone

class PermitApplicationFilter(filters.FilterSet):
    start_date = filters.DateFilter(field_name='application_date__date', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='application_date__date', lookup_expr='lte')
    min_quantity = filters.NumberFilter(method='filter_min_quantity')
    max_quantity = filters.NumberFilter(method='filter_max_quantity')
    search = filters.CharFilter(method='search_filter')
    delivery_start = filters.DateFilter(field_name='delivery_start', lookup_expr='gte')
    delivery_end = filters.DateFilter(field_name='delivery_end', lookup_expr='lte')
    is_valid = filters.BooleanFilter(method='filter_by_validity')

    class Meta:
        model = PermitApplication
        fields = ['status', 'society', 'factory', 'warehouse', 'min_quantity', 'max_quantity']

    def filter_min_quantity(self, queryset, name, value):
        return queryset.filter(total_weight__gte=value)

    def filter_max_quantity(self, queryset, name, value):
        return queryset.filter(total_weight__lte=value)

    def filter_by_validity(self, queryset, name, value):
        if value:
            return queryset.filter(
                status='APPROVED',
                delivery_start__lte=timezone.now().date(),
                delivery_end__gte=timezone.now().date()
            )
        return queryset.exclude(
            status='APPROVED',
            delivery_start__lte=timezone.now().date(),
            delivery_end__gte=timezone.now().date()
        )

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            Q(ref_no__icontains=value) |
            Q(farmer__first_name__icontains=value) |
            Q(farmer__last_name__icontains=value) |
            Q(society__name__icontains=value) |
            Q(factory__name__icontains=value) |
            Q(warehouse__name__icontains=value)
        )
