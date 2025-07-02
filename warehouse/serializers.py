from rest_framework import serializers
from .models import Warehouse


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = [
            "id",
            "name",
            "county",
            "sub_county",
            "licence_number",
            "is_active",
            "date_created",
            "date_updated",
            "created_by",
            "updated_by",
        ]
        read_only_fields = ["date_created", "date_updated", "created_by", "updated_by"]

    def validate_licence_number(self, value):
        qs = Warehouse.objects.filter(licence_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A warehouse with this licence number already exists."
            )
        return value
