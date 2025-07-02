from rest_framework import serializers
from .models import CoffeeGrade, PermitApplication, CoffeeQuantity
from users.models import CustomUser
from users.serializers import UserSerializer
from societies.models import Society, Factory
from societies.serializers import SocietySerializer, FactorySerializer
from warehouse.models import Warehouse
from warehouse.serializers import WarehouseSerializer
from django.core.validators import MinValueValidator
from users.utils import notify_admins


class CoffeeGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoffeeGrade
        fields = ['id', 'grade', 'weight_per_bag', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CoffeeQuantitySerializer(serializers.ModelSerializer):
    coffee_grade = CoffeeGradeSerializer(read_only=True)
    coffee_grade_id = serializers.PrimaryKeyRelatedField(
        queryset=CoffeeGrade.objects.all(),
        source='coffee_grade',
        write_only=True
    )
    total_weight = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    bags_quantity = serializers.IntegerField(
        validators=[MinValueValidator(1)],
        error_messages={'min_value': 'Number of bags must be at least 1'}
    )

    class Meta:
        model = CoffeeQuantity
        fields = ['id', 'coffee_grade', 'coffee_grade_id', 'bags_quantity', 'total_weight']
        read_only_fields = ['id', 'total_weight']


class PermitApplicationSerializer(serializers.ModelSerializer):
    farmer = UserSerializer(read_only=True)
    farmer_id = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        source='farmer',
        write_only=True
    )
    society = SocietySerializer(read_only=True)
    society_id = serializers.PrimaryKeyRelatedField(
        queryset=Society.objects.all(),
        source='society',
        write_only=True
    )
    factory = FactorySerializer(read_only=True)
    factory_id = serializers.PrimaryKeyRelatedField(
        queryset=Factory.objects.all(),
        source='factory',
        write_only=True
    )
    warehouse = WarehouseSerializer(read_only=True)
    warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(),
        source='warehouse',
        write_only=True
    )
    approved_by = UserSerializer(read_only=True)
    rejected_by = UserSerializer(read_only=True)
    coffee_quantities = CoffeeQuantitySerializer(many=True, read_only=True)
    total_bags = serializers.IntegerField(read_only=True)
    total_weight = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = PermitApplication
        fields = [
            'id', 'ref_no', 'farmer', 'farmer_id', 'society', 'society_id',
            'factory', 'factory_id', 'warehouse', 'warehouse_id',
            'application_date', 'delivery_start', 'delivery_end',
            'approved_by', 'approved_at', 'rejected_by', 'rejected_at',
            'rejection_reason', 'status', 'coffee_quantities',
            'total_bags', 'total_weight', 'is_valid'
        ]
        read_only_fields = [
            'id', 'ref_no', 'application_date', 'approved_at',
            'rejected_at', 'total_bags', 'total_weight', 'is_valid',
            'delivery_start', 'delivery_end'
        ]

    def validate(self, data):
        """
        Validate the permit application data
        """
        
        if 'delivery_start' in data or 'delivery_end' in data:
            if self.instance is None:
                data.pop('delivery_start', None)
                data.pop('delivery_end', None)
        
        if self.instance and 'status' in data:
            current_status = self.instance.status
            new_status = data['status']
            
            if current_status == 'APPROVED' and new_status != 'EXPIRED':
                raise serializers.ValidationError(
                    "Approved permits can only be expired"
                )
            
            if current_status in ['REJECTED', 'CANCELLED', 'EXPIRED']:
                raise serializers.ValidationError(
                    f"Cannot change status of {current_status.lower()} permit"
                )
        
        return data


class PermitApplicationCreateSerializer(serializers.ModelSerializer):
    coffee_quantities = CoffeeQuantitySerializer(many=True)
    society_id = serializers.PrimaryKeyRelatedField(
        queryset=Society.objects.all(),
        source='society',
        write_only=True
    )
    factory_id = serializers.PrimaryKeyRelatedField(
        queryset=Factory.objects.all(),
        source='factory',
        write_only=True
    )
    warehouse_id = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.all(),
        source='warehouse',
        write_only=True
    )

    class Meta:
        model = PermitApplication
        fields = [
            'id', 'society_id', 'factory_id', 'warehouse_id',
            'coffee_quantities'
        ]
        read_only_fields = ['id']

    def validate(self, data):
        user = self.context['request'].user
        
        try:
            managed_society_instance = user.managed_society
        except Society.DoesNotExist:
            raise serializers.ValidationError("Only society managers can apply for permits")

        society = data.get('society')
        factory = data.get('factory')
        warehouse = data.get('warehouse')
        
        if managed_society_instance != society:
            raise serializers.ValidationError("You can only apply for permits for your own society")
        
        if factory.society != society:
            raise serializers.ValidationError("Factory must belong to the selected society")
        if not factory.is_active:
            raise serializers.ValidationError("Selected factory is not active")
        
        if not warehouse.is_active:
            raise serializers.ValidationError("Selected warehouse is not active")
        
        coffee_quantities = data.get('coffee_quantities', [])
        if not coffee_quantities:
            raise serializers.ValidationError("At least one coffee quantity is required")
        
        return data

    def create(self, validated_data):
        coffee_quantities_data = validated_data.pop('coffee_quantities')
        society = validated_data.pop('society')
        factory = validated_data.pop('factory')
        warehouse = validated_data.pop('warehouse')
        
        # Set the farmer to the society manager
        validated_data['farmer'] = society.manager

        # Create the PermitApplication instance first. This will assign its PK.
        permit = PermitApplication.objects.create(
            society=society,
            factory=factory,
            warehouse=warehouse,
            **validated_data
        )

        # Create CoffeeQuantity instances AFTER permit is created to link them
        for cq_data in coffee_quantities_data:
            coffee_grade = cq_data.pop('coffee_grade')
            CoffeeQuantity.objects.create(
                application=permit,
                coffee_grade=coffee_grade,
                bags_quantity=cq_data['bags_quantity']
            )

        # Notify admins of new permit application
        notify_admins(
            type="NEW_PERMIT",
            message=f"A new permit application has been submitted by {society.name}.",
            link=f"/admin/permits/{permit.id}"
        )

        return permit


class PermitApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermitApplication
        fields = ['status', 'rejection_reason']
        read_only_fields = ['status']

    def validate(self, data):
        if 'status' in data:
            raise serializers.ValidationError("Status can only be changed through specific actions")
        return data