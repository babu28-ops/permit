from rest_framework import serializers
from .models import Society, Factory, CoffeePrice, AuditLog
from users.models import CustomUser
from django.contrib.auth import get_user_model
from django.contrib.auth.models import BaseUserManager
import secrets
import string
from django.db import transaction

User = get_user_model()

def generate_random_password(length=12):
    """Generates a secure random password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

class SocietySerializer(serializers.ModelSerializer):
    manager_name = serializers.SerializerMethodField()
    manager_email = serializers.SerializerMethodField()
    manager_phone = serializers.SerializerMethodField()
    rejected_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Society
        fields = [
            'id',
            'name',
            'manager',
            'manager_name',
            'manager_email',
            'manager_phone',
            'county',
            'sub_county',
            'is_approved',
            'date_registered',
            'date_approved',
            'approved_by',
            'rejection_reason',
            'date_rejected',
            'rejected_by',
            'rejected_by_name'
        ]
        read_only_fields = [
            'date_registered',
            'date_approved',
            'date_rejected'
        ]

    def get_manager_name(self, obj):
        return f"{obj.manager.first_name} {obj.manager.last_name}"

    def get_manager_email(self, obj):
        return obj.manager.email

    def get_manager_phone(self, obj):
        return obj.manager.phone_no

    def get_rejected_by_name(self, obj):
        if obj.rejected_by:
            return f"{obj.rejected_by.first_name} {obj.rejected_by.last_name} ({obj.rejected_by.email})"
        return "-"

class FactorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Factory
        fields = [
            'id',
            'society',
            'name',
            'is_active',
            'county',
            'sub_county',
            'date_added',
            'date_updated'
        ]
        read_only_fields = ['date_added', 'date_updated']

class CoffeePriceSerializer(serializers.ModelSerializer):
    coffee_grade_details = serializers.SerializerMethodField()
    
    class Meta:
        model = CoffeePrice
        fields = [
            'id',
            'society',
            'coffee_grade',
            'coffee_grade_details',
            'coffee_year',
            'price_per_bag',
            'effective_date',
            'is_active',
            'date_set'
        ]
        read_only_fields = ['date_set']

    def get_coffee_grade_details(self, obj):
        return {
            'grade': obj.coffee_grade.grade,
            'weight_per_bag': obj.coffee_grade.weight_per_bag
        }

class SocietyRegistrationSerializer(serializers.ModelSerializer):
    # Primary User Information
    email = serializers.EmailField(required=True)
    phone_no = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    # Secondary Society Information
    society_name = serializers.CharField(required=True)
    county = serializers.CharField(required=True)
    sub_county = serializers.CharField(required=True)

    class Meta:
        model = Society
        fields = [
            'email', 'phone_no', 'password', 'password2',
            'first_name', 'last_name',
            'society_name', 'county', 'sub_county'
        ]

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        if CustomUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({
                "email": "A user with this email already exists."
            })
        
        if CustomUser.objects.filter(phone_no=data['phone_no']).exists():
            raise serializers.ValidationError({
                "phone_no": "A user with this phone number already exists."
            })
        
        if Society.objects.filter(name__iexact=data['society_name']).exists():
            raise serializers.ValidationError({
                "society_name": "A society with this name already exists."
            })
        
        return data

    def create(self, validated_data):
        with transaction.atomic():
            # Extract user data
            user_data = {
                'email': validated_data.pop('email'),
                'phone_no': validated_data.pop('phone_no'),
                'password': validated_data.pop('password'),
                'first_name': validated_data.pop('first_name'),
                'last_name': validated_data.pop('last_name'),
                'role': 'FARMER',
                'is_active': False 
            }
            validated_data.pop('password2') 

            # Create the CustomUser
            user = CustomUser.objects.create_user(**user_data)
            
            # Extract society data
            society_data = {
                'name': validated_data.pop('society_name'),
                'manager': user,  
                'county': validated_data.pop('county'),
                'sub_county': validated_data.pop('sub_county'),
                'is_approved': False 
            }
            
            # Create the Society
            society = Society.objects.create(**society_data)
            return society
        
        
class AdminSocietyRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    phone_no = serializers.CharField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    society_name = serializers.CharField(required=True)
    county = serializers.CharField(required=True)
    sub_county = serializers.CharField(required=True)

    def validate(self, data):
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})
        if User.objects.filter(phone_no=data['phone_no']).exists():
            raise serializers.ValidationError({"phone_no": "A user with this phone number already exists."})
        if Society.objects.filter(name__iexact=data['society_name']).exists():
            raise serializers.ValidationError({"society_name": "A society with this name already exists."})
        return data

    def create(self, validated_data):
        from django.core.mail import send_mail
        from django.conf import settings

        password = generate_random_password()
        user = User.objects.create_user(
            email=validated_data['email'],
            phone_no=validated_data['phone_no'],
            password=password,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            role='FARMER',
            is_active=True  # Immediately active
        )
        society = Society.objects.create(
            name=validated_data['society_name'],
            manager=user,
            county=validated_data['county'],
            sub_county=validated_data['sub_county'],
            is_approved=True  # Immediately approved
        )

        send_mail(
            subject="Your Society Manager Account",
            message=f"Hello {user.first_name},\n\nYour account has been created by the admin. Your temporary password is: {password}\nPlease log in and change your password as soon as possible.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return society

class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id', 'action', 'model', 'object_id', 'timestamp', 'ip_address', 'user_agent', 'details'
        ]
