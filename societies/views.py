from django.shortcuts import render
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import Society, Factory, CoffeePrice, AuditLog
from .serializers import (
    SocietyRegistrationSerializer,
    SocietySerializer,
    FactorySerializer,
    CoffeePriceSerializer,
    AdminSocietyRegistrationSerializer,
    AuditLogSerializer,
)
from django.utils import timezone
from django.db import IntegrityError, transaction
from .permissions import IsSocietyManager, IsAdminOrReadOnly, IsSocietyApproved
from .throttling import AdminActionThrottle, SocietyActionThrottle, RegistrationThrottle
from rest_framework.generics import ListAPIView
from users.utils import notify_admins, notify_user

# Registration Views
class SocietyRegistrationView(generics.CreateAPIView):
    """
    Handles the combined two-step society registration process.
    Creates both the user and the society, setting them as inactive/unapproved.
    """
    permission_classes = [AllowAny]
    serializer_class = SocietyRegistrationSerializer
    # throttle_classes = [RegistrationThrottle]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                # Create user and society within a transaction
                with transaction.atomic():
                    society = serializer.save()
                # Notify admin about new registration
                notify_admins(
                    type="SOCIETY_REGISTRATION_SUBMITTED",
                    message=f"New society registration submitted: {society.name}",
                    link=f"/admin/societies/{society.id}"
                )
                return Response({
                    'message': 'Application submitted successfully. Please wait for approval.',
                    'society_id': society.id,
                    'user_id': society.manager.id
                }, status=status.HTTP_201_CREATED)
            # Handle validation errors
            # Log the specific error for audit, but do not reveal to client
            return Response({
                'error': 'Registration failed. Please check your details and try again.'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': 'An error occurred during registration. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SocietyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsSocietyManager]
    serializer_class = SocietySerializer

    def get_queryset(self):
        if self.request.user.role == 'ADMIN':
            return Society.objects.all()
        return Society.objects.filter(manager=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        with transaction.atomic():
            society = serializer.save(manager=self.request.user)
            # Add audit logging here if implemented

    def perform_update(self, serializer):
        if not self.request.user.can_perform_action('manage_own_society'):
            raise PermissionDenied("You don't have permission to update this society")
        serializer.save()

class AdminSocietyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    # throttle_classes = [AdminActionThrottle]
    serializer_class = SocietySerializer

    def get_queryset(self):
        if self.request.user.role == 'ADMIN':
            return Society.objects.all().order_by("-date_registered")
        return Society.objects.filter(manager=self.request.user)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def approve(self, request, pk=None):

        society = self.get_object()
        
        # Check if already approved or rejected
        if society.is_approved:
            return Response(
                {'error': 'Society is already approved'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if society.rejection_reason:
            return Response(
                {'error': 'Cannot approve a rejected society'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Perform approval with transaction
        with transaction.atomic():
            society.is_approved = True
            society.approved_by = request.user
            society.date_approved = timezone.now()
            society.manager.is_active = True
            society.manager.save()
            society.save()

            # Log the action
            AuditLog.objects.create(
                user=request.user,
                action='APPROVE_SOCIETY',
                model='Society',
                object_id=society.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                details={}
            )

            # Send notification to manager
            notify_user(society.manager,
                type="SOCIETY_APPROVED",
                message=f"Your society '{society.name}' has been approved.",
                link=f"/societies/{society.id}"
            )

        return Response({
            'status': 'society approved',
            'date_approved': society.date_approved
        })

    @action(detail=True, methods=['post'])
    @transaction.atomic 
    def reject(self, request, pk=None):
        society = self.get_object()
        
        # Check if already approved or rejected
        if society.is_approved:
            return Response(
                {'error': 'Cannot reject an approved society'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        if society.rejection_reason:
            return Response(
                {'error': 'Society is already rejected'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        rejection_reason = request.data.get('rejection_reason')
        if not rejection_reason:
            return Response(
                {'error': 'Rejection reason is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic(): 
            society.rejection_reason = rejection_reason
            society.date_rejected = timezone.now()
            society.rejected_by = request.user
            society.save()

            # Log the rejection action (RECOMMENDED ADDITION)
            AuditLog.objects.create(
                user=request.user,
                action='REJECT_SOCIETY',
                model='Society',
                object_id=society.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                details={'rejection_reason': rejection_reason}
            )

            # Send notification to manager
            notify_user(society.manager,
                type="SOCIETY_REJECTED",
                message=f"Your society '{society.name}' registration was rejected. Reason: {rejection_reason}",
                link=f"/societies/{society.id}"
            )
        
        return Response({
            'status': 'society rejected',
            'rejection_reason': society.rejection_reason,
            'date_rejected': society.date_rejected
        })

    @action(detail=False, methods=['get'])
    def get_pending_registrations(self, request):
        pending = Society.objects.filter(
            is_approved=False,
            rejection_reason__isnull=True
        )
        serializer = self.get_serializer(pending, many=True)
        return Response(serializer.data)

class FactoryViewSet(viewsets.ModelViewSet):
    serializer_class = FactorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'ADMIN':
            return Factory.objects.all().order_by('-date_added')
        return Factory.objects.filter(society__manager=self.request.user).order_by('-date_added')

    def perform_create(self, serializer):
        society = serializer.validated_data.get('society')
        if self.request.user.role != 'ADMIN' and society.manager != self.request.user:
            raise PermissionDenied("You can only create factories for your own society.")
        serializer.save()

    def perform_update(self, serializer):
        factory = self.get_object()
        if self.request.user.role != 'ADMIN' and factory.society.manager != self.request.user:
            raise PermissionDenied("You can only update factories in your own society.")
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role != 'ADMIN' and instance.society.manager != self.request.user:
            raise PermissionDenied("You can only delete factories in your own society.")
        instance.delete()

    @action(detail=False, methods=['get'])
    def active_factories(self, request):
        """Get only active factories for permit applications"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class CoffeePriceViewSet(viewsets.ModelViewSet):
    serializer_class = CoffeePriceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CoffeePrice.objects.select_related('society', 'coffee_grade')
        if self.request.user.role == 'ADMIN':
            return queryset
        # For non-admin users, filter prices by their managed society
        return queryset.filter(society__manager=self.request.user)

    def perform_create(self, serializer):
        print(f"User role: {self.request.user.role}")
        print(f"User ID: {self.request.user.id}")
        
        # Check if the user has a managed_society attribute
        has_managed_society = hasattr(self.request.user, 'managed_society')
        print(f"User has managed_society: {has_managed_society}")

        if has_managed_society:
            print(f"Managed society ID: {self.request.user.managed_society.id}")
            print(f"Managed society name: {self.request.user.managed_society.name}")
            print(f"Managed society approved: {self.request.user.managed_society.is_approved}")


        # If the user is a society manager, automatically set the society
        if self.request.user.role == 'FARMER' and has_managed_society:
            # Ensure the user is not trying to set a different society
            if 'society' in serializer.validated_data and serializer.validated_data['society'] != self.request.user.managed_society:
                raise PermissionDenied("You can only set coffee prices for your own society.")
            
            serializer.validated_data['society'] = self.request.user.managed_society
            print(f"Assigned society: {serializer.validated_data['society'].name}")
        elif self.request.user.role != 'ADMIN':
            raise PermissionDenied("You don't have permission to set coffee prices.")
        
        effective_date = serializer.validated_data.get('effective_date')
        today = timezone.now().date()
        serializer.validated_data['is_active'] = effective_date <= today
        
        try:
            # Validate coffee year format
            coffee_year = serializer.validated_data.get('coffee_year')
            import re
            if not re.match(r'^\d{4}/\d{2}$', coffee_year):
                raise ValidationError({
                    'coffee_year': 'Coffee year must be in format YYYY/YY (e.g., 2023/24)'
                })
            
            serializer.save()
        except IntegrityError:
            raise ValidationError({
                'error': 'A price for this grade and year already exists for this society'
            })

    def perform_update(self, serializer):
        coffee_price = self.get_object()
        if self.request.user.role == 'FARMER' and coffee_price.society.manager != self.request.user:
            raise PermissionDenied("You can only update coffee prices in your own society.")
        elif self.request.user.role != 'ADMIN':
            raise PermissionDenied("You don't have permission to update coffee prices.")
        
        effective_date = serializer.validated_data.get('effective_date')
        today = timezone.now().date()
        serializer.validated_data['is_active'] = effective_date <= today
        
        try:
            # Validate coffee year format
            coffee_year = serializer.validated_data.get('coffee_year')
            import re
            if not re.match(r'^\d{4}/\d{2}$', coffee_year):
                raise ValidationError({
                    'coffee_year': 'Coffee year must be in format YYYY/YY (e.g., 2023/24)'
                })
            
            serializer.save()
        except IntegrityError:
            raise ValidationError({
                'error': 'A price for this grade and year already exists for this society'
            })

    def perform_destroy(self, instance):
        if self.request.user.role == 'FARMER' and instance.society.manager != self.request.user:
            raise PermissionDenied("You can only delete coffee prices in your own society.")
        elif self.request.user.role != 'ADMIN':
            raise PermissionDenied("You don't have permission to delete coffee prices.")
        instance.delete()

    @action(detail=False, methods=['get'])
    def active_prices(self, request):
        """Get only active prices for the current coffee year"""
        from django.utils import timezone
        current_date = timezone.now().date()
        
        # Determine current coffee year
        if current_date.month < 10:
            coffee_year = f"{current_date.year - 1}/{str(current_date.year)[-2:]}"
        else:
            coffee_year = f"{current_date.year}/{str(current_date.year + 1)[-2:]}"
        
        queryset = self.get_queryset().filter(
            coffee_year=coffee_year,
            is_active=True
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class AdminSocietyRegistrationView(generics.CreateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminSocietyRegistrationSerializer

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        society = serializer.save()
        # Use SocietySerializer for the response
        return Response(SocietySerializer(society).data, status=status.HTTP_201_CREATED)

class AuditLogListView(ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = AuditLog.objects.all().order_by('-timestamp')
        user_id = self.request.query_params.get('user')
        action = self.request.query_params.get('action')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if action:
            queryset = queryset.filter(action__icontains=action)
        if start_date:
            queryset = queryset.filter(timestamp__gte=start_date)
        if end_date:
            queryset = queryset.filter(timestamp__lte=end_date)
        return queryset

    def list(self, request, *args, **kwargs):
        if request.query_params.get('format') == 'csv':
            import csv
            from django.http import HttpResponse
            queryset = self.get_queryset()
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
            writer = csv.writer(response)
            writer.writerow(['ID', 'User', 'Action', 'Model', 'Object ID', 'Timestamp', 'IP Address', 'User Agent', 'Details'])
            for log in queryset:
                writer.writerow([
                    log.id,
                    log.user.email if log.user else '',
                    log.action,
                    log.model,
                    log.object_id,
                    log.timestamp,
                    log.ip_address,
                    log.user_agent,
                    log.details
                ])
            return response
        return super().list(request, *args, **kwargs)
