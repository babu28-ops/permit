from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import (
    action,
    api_view,
    permission_classes,
    throttle_classes,
)
from rest_framework.response import Response
from django.utils import timezone
from .models import PermitApplication, CoffeeGrade, CoffeeQuantity
from .serializers import (
    PermitApplicationSerializer,
    PermitApplicationCreateSerializer,
    PermitApplicationUpdateSerializer,
    CoffeeGradeSerializer,
    CoffeeQuantitySerializer,
)
from django.db.models import Q, F, Sum, FloatField, Count
from django_filters.rest_framework import DjangoFilterBackend
from .filters import PermitApplicationFilter
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.http import HttpResponse
from django.conf import settings
import os
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from django.core.exceptions import ObjectDoesNotExist
from .throttling import (
    SocietyManagerRateThrottle,
    StaffRateThrottle,
    FarmerRateThrottle,
    AnonRateThrottle,
)
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncQuarter
import datetime
from datetime import timedelta
import pandas as pd
from rest_framework.pagination import PageNumberPagination
from users.utils import notify_user


class IsSocietyManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.managed_society is not None


class CoffeeGradeViewSet(viewsets.ModelViewSet):
    queryset = CoffeeGrade.objects.all()
    serializer_class = CoffeeGradeSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [StaffRateThrottle]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class PermitApplicationViewSet(viewsets.ModelViewSet):
    queryset = PermitApplication.objects.all().order_by("-application_date")
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PermitApplicationFilter
    pagination_class = StandardResultsSetPagination

    def get_throttles(self):
        if self.request.user.is_staff:
            return [StaffRateThrottle()]
        elif self.request.user.managed_society is not None:
            return [SocietyManagerRateThrottle()]
        else:
            return [FarmerRateThrottle()]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsSocietyManager()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return PermitApplicationCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return PermitApplicationUpdateSerializer
        return PermitApplicationSerializer

    def create(self, request, *args, **kwargs):
        try:
            print("Data received in PermitApplicationViewSet create:", request.data)
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Update status for each permit in the queryset
        for permit in queryset:
            permit.update_status()

        # Filter based on user role
        if user.is_staff:
            return queryset  # Staff sees all permits
        elif user.managed_society is not None:
            return queryset.filter(
                society__manager=user
            )  # Manager sees only their society's permits
        else:
            return queryset.filter(
                farmer=user
            )  # Regular farmers see only their permits

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        permit = self.get_object()

        if permit.status != "PENDING":
            return Response(
                {"error": "Only pending permits can be approved"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permit.status = "APPROVED"
        permit.approved_by = request.user
        permit.approved_at = timezone.now()
        permit.save()

        # Notify the permit owner (society manager)
        notify_user(permit.society.manager,
            type="PERMIT_APPROVED",
            message=f"Your permit application (Ref: {permit.ref_no}) has been approved.",
            link=f"/permits/{permit.id}"
        )
        # Notify the farmer if different from manager
        if permit.farmer and permit.farmer != permit.society.manager:
            notify_user(permit.farmer,
                type="PERMIT_APPROVED",
                message=f"Your permit application (Ref: {permit.ref_no}) has been approved.",
                link=f"/permits/{permit.id}"
            )

        serializer = self.get_serializer(permit)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        permit = self.get_object()

        if permit.status != "PENDING":
            return Response(
                {"error": "Only pending permits can be rejected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rejection_reason = request.data.get("rejection_reason")
        if not rejection_reason:
            return Response(
                {"error": "Rejection reason is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permit.status = "REJECTED"
        permit.rejection_reason = rejection_reason
        permit.rejected_by = request.user
        permit.rejected_at = timezone.now()
        permit.save()

        # Notify the permit owner (society manager)
        notify_user(permit.society.manager,
            type="PERMIT_REJECTED",
            message=f"Your permit application (Ref: {permit.ref_no}) has been rejected. Reason: {rejection_reason}",
            link=f"/permits/{permit.id}"
        )
        # Notify the farmer if different from manager
        if permit.farmer and permit.farmer != permit.society.manager:
            notify_user(permit.farmer,
                type="PERMIT_REJECTED",
                message=f"Your permit application (Ref: {permit.ref_no}) has been rejected. Reason: {rejection_reason}",
                link=f"/permits/{permit.id}"
            )

        serializer = self.get_serializer(permit)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        permit = self.get_object()

        if permit.status not in ["PENDING", "APPROVED"]:
            return Response(
                {"error": "Only pending or approved permits can be cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        permit.status = "CANCELLED"
        permit.save()

        # Notify the permit owner (society manager)
        notify_user(permit.society.manager,
            type="PERMIT_CANCELLED",
            message=f"Your permit application (Ref: {permit.ref_no}) has been cancelled.",
            link=f"/permits/{permit.id}"
        )
        # Notify the farmer if different from manager
        if permit.farmer and permit.farmer != permit.society.manager:
            notify_user(permit.farmer,
                type="PERMIT_CANCELLED",
                message=f"Your permit application (Ref: {permit.ref_no}) has been cancelled.",
                link=f"/permits/{permit.id}"
            )

        serializer = self.get_serializer(permit)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def my_permits(self, request):
        queryset = PermitApplication.objects.all()
        if request.user.managed_society is not None:
            queryset = queryset.filter(society__manager=request.user)
        else:
            queryset = queryset.filter(farmer=request.user)

        # Apply filters
        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        start_date = request.query_params.get("start_date")
        if start_date:
            queryset = queryset.filter(application_date__gte=start_date)
        end_date = request.query_params.get("end_date")
        if end_date:
            queryset = queryset.filter(application_date__lte=end_date)
        society = request.query_params.get("society")
        if society:
            queryset = queryset.filter(society_id=society)
        factory = request.query_params.get("factory")
        if factory:
            queryset = queryset.filter(factory_id=factory)
        warehouse = request.query_params.get("warehouse")
        if warehouse:
            queryset = queryset.filter(warehouse_id=warehouse)
        min_quantity = request.query_params.get("min_quantity")
        if min_quantity:
            queryset = queryset.filter(total_weight__gte=min_quantity)
        max_quantity = request.query_params.get("max_quantity")
        if max_quantity:
            queryset = queryset.filter(total_weight__lte=max_quantity)

        queryset = queryset.order_by("-application_date")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def pending_permits(self, request):
        queryset = self.get_queryset()

        # Filter for pending permits
        pending_permits = queryset.filter(status="PENDING")

        # Apply role-based filtering
        if not request.user.is_staff:
            if request.user.managed_society is not None:
                # For society managers, show only their society's pending permits
                pending_permits = pending_permits.filter(society__manager=request.user)
            else:
                # For regular farmers, show only their pending permits
                pending_permits = pending_permits.filter(farmer=request.user)

        serializer = self.get_serializer(pending_permits, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def society_metrics(self, request):
        if not request.user.managed_society is not None:
            return Response(
                {"error": "Only society managers can access these metrics"},
                status=status.HTTP_403_FORBIDDEN,
            )

        society_permits = PermitApplication.objects.filter(
            society__manager=request.user
        )
        total_permits = society_permits.count()
        active_permits = society_permits.filter(status="APPROVED").count()
        pending_permits = society_permits.filter(status="PENDING").count()
        expired_permits = society_permits.filter(status="EXPIRED").count()

        return Response(
            {
                "total_permits": total_permits,
                "active_permits": active_permits,
                "pending_permits": pending_permits,
                "expired_permits": expired_permits,
            }
        )

    @action(detail=False, methods=["get"])
    def staff_metrics(self, request):

        if not request.user.is_staff:
            return Response(
                {"error": "Only staff members can access these metrics"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Get all permits
        all_permits = self.get_queryset()

        # Basic counts
        total_permits = all_permits.count()
        active_permits = all_permits.filter(status="APPROVED").count()
        pending_permits = all_permits.filter(status="PENDING").count()
        expired_permits = all_permits.filter(status="EXPIRED").count()
        rejected_permits = all_permits.filter(status="REJECTED").count()

        return Response(
            {
                "total_permits": total_permits,
                "active_permits": active_permits,
                "pending_permits": pending_permits,
                "expired_permits": expired_permits,
                "rejected_permits": rejected_permits,
            }
        )

    @action(detail=False, methods=["post"])
    def bulk_approve(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Only staff members can approve permits"},
                status=status.HTTP_403_FORBIDDEN,
            )
        permit_ids = request.data.get("permit_ids", [])
        if not permit_ids:
            return Response(
                {"error": "No permit IDs provided"}, status=status.HTTP_400_BAD_REQUEST
            )
        permits = PermitApplication.objects.filter(id__in=permit_ids, status="PENDING")
        if not permits.exists():
            return Response(
                {"error": "No valid pending permits found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        current_time = timezone.now()
        for permit in permits:
            permit.status = "APPROVED"
            permit.approved_by = request.user
            permit.approved_at = current_time
            permit.save()
        serializer = self.get_serializer(permits, many=True)
        return Response(
            {
                "message": f"Successfully approved {permits.count()} permits",
                "permits": serializer.data,
            }
        )

    @action(detail=False, methods=["post"])
    def bulk_reject(self, request):
        if not request.user.is_staff:
            return Response(
                {"error": "Only staff members can reject permits"},
                status=status.HTTP_403_FORBIDDEN,
            )
        permit_ids = request.data.get("permit_ids", [])
        rejection_reason = request.data.get("rejection_reason")
        if not permit_ids:
            return Response(
                {"error": "No permit IDs provided"}, status=status.HTTP_400_BAD_REQUEST
            )
        if not rejection_reason:
            return Response(
                {"error": "Rejection reason is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        permits = PermitApplication.objects.filter(id__in=permit_ids, status="PENDING")
        if not permits.exists():
            return Response(
                {"error": "No valid pending permits found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        current_time = timezone.now()
        for permit in permits:
            permit.status = "REJECTED"
            permit.rejection_reason = rejection_reason
            permit.rejected_by = request.user
            permit.rejected_at = current_time
            permit.save()
        serializer = self.get_serializer(permits, many=True)
        return Response(
            {
                "message": f"Successfully rejected {permits.count()} permits",
                "permits": serializer.data,
            }
        )

    @action(detail=False, methods=["get"], url_path="analytics")
    def analytics(self, request):
        """
        Returns permit counts grouped by period (day/week/month) and status.
        Query params:
            - start_date: YYYY-MM-DD
            - end_date: YYYY-MM-DD
            - granularity: daily|weekly|monthly (default: daily)
            - status, society, factory, warehouse, etc. (optional filters)
        """
        # Get filters from query params
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        granularity = request.query_params.get("granularity", "daily")

        # Base queryset with filters
        queryset = self.filter_queryset(self.get_queryset())
        if start_date:
            queryset = queryset.filter(application_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(application_date__lte=end_date)

        # Choose truncation function based on granularity
        if granularity == "weekly":
            trunc_func = TruncWeek("application_date")
        elif granularity == "monthly":
            trunc_func = TruncMonth("application_date")
        else:
            trunc_func = TruncDay("application_date")

        # Group by period and status, count
        grouped = (
            queryset
            .annotate(period=trunc_func)
            .values("period", "status")
            .order_by("period")
            .annotate(count=Count("id"))
        )

        # Pivot to {period: {status1: count, status2: count, ...}}
        result = {}
        for row in grouped:
            period = row["period"].strftime("%Y-%m-%d") if granularity == "daily" else row["period"].strftime("%Y-%m")
            if granularity == "weekly":
                period = f"{row['period'].isocalendar()[0]}-W{row['period'].isocalendar()[1]:02d}"
            if period not in result:
                result[period] = {}
            result[period][row["status"]] = row["count"]

        # Ensure all statuses are present for each period (fill missing with 0)
        all_statuses = [choice[0] for choice in self.queryset.model.STATUS_CHOICES]
        chart_data = []
        for period in sorted(result.keys()):
            entry = {"period": period}
            for status in all_statuses:
                entry[status] = result[period].get(status, 0)
            chart_data.append(entry)

        page = self.paginate_queryset(chart_data)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(chart_data)

    @action(detail=False, methods=["get"], url_path="coffee-analytics", throttle_classes=[AnonRateThrottle, StaffRateThrottle])
    def coffee_analytics(self, request):
        """
        Returns total coffee moved grouped by period (day/week/month) and grade.
        Query params:
            - start_date: YYYY-MM-DD
            - end_date: YYYY-MM-DD
            - granularity: daily|weekly|monthly (default: daily)
            - society, factory, warehouse, etc. (optional filters)
        """
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        granularity = request.query_params.get("granularity", "daily")

        # Filter permits by date and other filters
        permits = self.filter_queryset(self.get_queryset())
        if start_date:
            permits = permits.filter(application_date__date__gte=start_date)
        if end_date:
            permits = permits.filter(application_date__date__lte=end_date)

        # Choose truncation function based on granularity
        if granularity == "weekly":
            trunc_func = TruncWeek("application__application_date")
        elif granularity == "monthly":
            trunc_func = TruncMonth("application__application_date")
        elif granularity == "90days":
            trunc_func = TruncQuarter("application__application_date")
        else:
            trunc_func = TruncDay("application__application_date")

        # Join with CoffeeQuantity and CoffeeGrade
        from .models import CoffeeQuantity, CoffeeGrade
        coffee_quantities = CoffeeQuantity.objects.filter(application__in=permits)

        # Annotate period and grade, sum total_weight
        grouped = (
            coffee_quantities
            .annotate(period=trunc_func)
            .values("period", "coffee_grade__grade")
            .annotate(total_weight=Sum(F("bags_quantity") * F("coffee_grade__weight_per_bag"), output_field=FloatField()))
            .order_by("period")
        )

        # Pivot to {period: {grade1: total, grade2: total, ...}}
        result = {}
        for row in grouped:
            if granularity == "daily":
                period = row["period"].strftime("%Y-%m-%d")
            elif granularity == "weekly":
                period = f"{row['period'].isocalendar()[0]}-W{row['period'].isocalendar()[1]:02d}"
            elif granularity == "monthly":
                period = row["period"].strftime("%Y-%m")
            elif granularity == "90days":
                period = f"{row['period'].year}-Q{((row['period'].month - 1) // 3) + 1}"
            else:
                period = str(row["period"])
            if period not in result:
                result[period] = {}
            result[period][row["coffee_grade__grade"]] = row["total_weight"]

        # Get all grades
        all_grades = list(CoffeeGrade.objects.values_list("grade", flat=True))
        chart_data = []

        # --- NEW: Ensure all periods (weeks/quarters) in range are present ---
        if granularity == "weekly":
            curr = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            first_week_start = curr - timedelta(days=curr.weekday())  # Monday as start of week
            last_week_start = end - timedelta(days=end.weekday())
            all_weeks = set()
            curr = first_week_start
            while curr <= last_week_start:
                year, week, _ = curr.isocalendar()
                week_key = f"{year}-W{week:02d}"
                all_weeks.add(week_key)
                curr += timedelta(days=7)
            for week in all_weeks:
                if week not in result:
                    result[week] = {}
            sorted_periods = sorted(all_weeks)
        elif granularity == "90days":
            curr = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            # Find the first quarter start
            first_quarter = pd.Timestamp(year=curr.year, month=3*((curr.month-1)//3)+1, day=1)
            last_quarter = pd.Timestamp(year=end.year, month=3*((end.month-1)//3)+1, day=1)
            all_quarters = set()
            curr = first_quarter
            while curr <= last_quarter:
                quarter_key = f"{curr.year}-Q{((curr.month-1)//3)+1}"
                all_quarters.add(quarter_key)
                # Move to next quarter
                if curr.month >= 10:
                    curr = pd.Timestamp(year=curr.year+1, month=1, day=1)
                else:
                    curr = pd.Timestamp(year=curr.year, month=curr.month+3, day=1)
            for quarter in all_quarters:
                if quarter not in result:
                    result[quarter] = {}
            sorted_periods = sorted(all_quarters)
        else:
            sorted_periods = sorted(result.keys())

        for period in sorted_periods:
            entry = {"period": period}
            for grade in all_grades:
                entry[grade] = result[period].get(grade, 0)
            chart_data.append(entry)
        # --- END NEW ---

        page = self.paginate_queryset(chart_data)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(chart_data)

    @action(detail=False, methods=["get"], url_path="top-societies", throttle_classes=[AnonRateThrottle, StaffRateThrottle])
    def top_societies(self, request):
        """
        Returns top societies by total coffee moved (with filters).
        Query params: start_date, end_date, factory, warehouse, etc.
        """
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        permits = self.filter_queryset(self.get_queryset())
        if start_date:
            permits = permits.filter(application_date__date__gte=start_date)
        if end_date:
            permits = permits.filter(application_date__date__lte=end_date)

        from .models import CoffeeQuantity

        # Join CoffeeQuantity and group by society
        coffee_quantities = CoffeeQuantity.objects.filter(application__in=permits)
        grouped = (
            coffee_quantities
            .values("application__society__id", "application__society__name")
            .annotate(total_kg=Sum(F("bags_quantity") * F("coffee_grade__weight_per_bag"), output_field=FloatField()))
            .order_by("-total_kg")
        )

        # Return top 3 (or all if you want)
        result = [
            {
                "society_id": row["application__society__id"],
                "society": row["application__society__name"],
                "totalKg": row["total_kg"] or 0,
            }
            for row in grouped
        ]
        page = self.paginate_queryset(result)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="top-grades", throttle_classes=[AnonRateThrottle, StaffRateThrottle])
    def top_grades(self, request):
        """
        Returns top coffee grades by total coffee moved (with filters).
        Query params: start_date, end_date, society, factory, warehouse, exclude_grades, etc.
        """
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        exclude_grades = request.query_params.get("exclude_grades")
        exclude_grades = exclude_grades.split(",") if exclude_grades else []

        permits = self.filter_queryset(self.get_queryset())
        if start_date:
            permits = permits.filter(application_date__date__gte=start_date)
        if end_date:
            permits = permits.filter(application_date__date__lte=end_date)

        from .models import CoffeeQuantity

        coffee_quantities = CoffeeQuantity.objects.filter(application__in=permits)
        if exclude_grades:
            coffee_quantities = coffee_quantities.exclude(coffee_grade__grade__in=exclude_grades)
        grouped = (
            coffee_quantities
            .values("coffee_grade__grade")
            .annotate(total_kg=Sum(F("bags_quantity") * F("coffee_grade__weight_per_bag"), output_field=FloatField()))
            .order_by("-total_kg")
        )

        result = [
            {
                "grade": row["coffee_grade__grade"],
                "totalKg": row["total_kg"] or 0,
            }
            for row in grouped
        ]
        page = self.paginate_queryset(result)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="permits-cumulative-status")
    def permits_cumulative_status(self, request):
        """
        Returns cumulative count of approved and rejected permits by day.
        """
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        qs = self.get_queryset().filter(status__in=["APPROVED", "REJECTED"])
        if start_date:
            qs = qs.filter(approved_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(approved_at__date__lte=end_date)

        # Get all relevant dates
        all_dates = set()
        for status in ["APPROVED", "REJECTED"]:
            date_field = "approved_at" if status == "APPROVED" else "rejected_at"
            status_qs = self.get_queryset().filter(status=status)
            if start_date:
                status_qs = status_qs.filter(**{f"{date_field}__date__gte": start_date})
            if end_date:
                status_qs = status_qs.filter(**{f"{date_field}__date__lte": end_date})
            all_dates.update(
                status_qs.annotate(day=TruncDay(date_field)).values_list("day", flat=True)
            )
        all_dates = sorted([d for d in all_dates if d is not None])

        # Build cumulative counts
        cumulative_approved = 0
        cumulative_rejected = 0
        result = []
        for day in all_dates:
            approved_count = self.get_queryset().filter(
                status="APPROVED", approved_at__date=day.date()
            ).count()
            rejected_count = self.get_queryset().filter(
                status="REJECTED", rejected_at__date=day.date()
            ).count()
            cumulative_approved += approved_count
            cumulative_rejected += rejected_count
            result.append({
                "date": day.strftime("%Y-%m-%d"),
                "cumulative_approved": cumulative_approved,
                "cumulative_rejected": cumulative_rejected,
            })

        return Response(result)

    @action(detail=False, methods=["get"], url_path="top-factories", throttle_classes=[AnonRateThrottle, StaffRateThrottle])
    def top_factories(self, request):
        """
        Returns top factories by total coffee moved (with filters).
        Query params: start_date, end_date, society, warehouse, exclude_grades, etc.
        """
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        society = request.query_params.get("society")
        warehouse = request.query_params.get("warehouse")
        exclude_grades = request.query_params.get("exclude_grades")
        exclude_grades = exclude_grades.split(",") if exclude_grades else []

        permits = self.filter_queryset(self.get_queryset())
        if start_date:
            permits = permits.filter(application_date__date__gte=start_date)
        if end_date:
            permits = permits.filter(application_date__date__lte=end_date)
        if society:
            permits = permits.filter(society_id=society)
        if warehouse:
            permits = permits.filter(warehouse_id=warehouse)

        from .models import CoffeeQuantity

        # Join CoffeeQuantity and group by factory
        coffee_quantities = CoffeeQuantity.objects.filter(application__in=permits)
        if exclude_grades:
            coffee_quantities = coffee_quantities.exclude(coffee_grade__grade__in=exclude_grades)
        grouped = (
            coffee_quantities
            .values("application__factory__id", "application__factory__name")
            .annotate(total_kg=Sum(F("bags_quantity") * F("coffee_grade__weight_per_bag"), output_field=FloatField()))
            .order_by("-total_kg")
        )

        # Return top 3 (or all if you want)
        result = [
            {
                "factory_id": row["application__factory__id"],
                "factory": row["application__factory__name"],
                "totalKg": row["total_kg"] or 0,
            }
            for row in grouped
        ]
        page = self.paginate_queryset(result)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(result)


class CoffeeQuantityViewSet(viewsets.ModelViewSet):
    queryset = CoffeeQuantity.objects.all()
    serializer_class = CoffeeQuantitySerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [FarmerRateThrottle]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return CoffeeQuantity.objects.all()
        return CoffeeQuantity.objects.filter(application__farmer=user)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def generate_permit_pdf(request, permit_id):
    try:
        permit = get_object_or_404(
            PermitApplication.objects.select_related(
                "society", "factory", "warehouse"
            ).prefetch_related("coffee_quantities__coffee_grade"),
            id=permit_id
        )
        # Update permit status before checking
        permit.update_status()
        # Check if permit is approved
        if permit.status != "APPROVED":
            raise PermissionDenied(
                detail=f"PDF can only be generated for approved permits. Current status: {permit.status}"
            )
        # Pre-fetch related data
        permit_data = {
            "ref_no": permit.ref_no,
            "status": permit.status,
            "application_date": permit.application_date,
            "delivery_start": permit.delivery_start,
            "delivery_end": permit.delivery_end,
            "rejection_reason": permit.rejection_reason,
            "total_bags": permit.total_bags,
            "total_weight": permit.total_weight,
            # Evaluate related fields
            "society": {
                "name": permit.society.name,
                "sub_county": permit.society.sub_county,
                "county": permit.society.county,
            },
            "factory": {
                "name": permit.factory.name,
                "county": permit.factory.county,
                "sub_county": permit.factory.sub_county,
            },
            "warehouse": {
                "name": permit.warehouse.name,
                "sub_county": permit.warehouse.sub_county,
                "county": permit.warehouse.county,
            },
            "coffee_quantities": [
                {
                    "id": item.id,
                    "bags_quantity": item.bags_quantity,
                    "total_weight": item.total_weight,
                    "coffee_grade": {
                        "grade": item.coffee_grade.grade,
                        "weight_per_bag": item.coffee_grade.weight_per_bag,
                    },
                }
                for item in permit.coffee_quantities.all()
            ],
        }
        html_string = render_to_string(
            "permits/permit_pdf.html",
            {
                "permit": permit_data,
            },
        )
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="permit_{permit.ref_no}.pdf"'
        pisa_status = pisa.CreatePDF(html_string, dest=response)
        if pisa_status.err:
            return HttpResponse("Error generating PDF", status=500)
        return response
    except Exception as e:
        return HttpResponse("Error generating PDF", status=500)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([AnonRateThrottle, StaffRateThrottle])
def analytics_report_pdf(request):
    try:
        user = request.user
        data = request.data
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        granularity = data.get("granularity", "monthly")
        include_total = data.get("include_total", True)
        include_top_factories = data.get("include_top_factories", True)
        include_top_societies = data.get("include_top_societies", True)
        include_top_grades = data.get("include_top_grades", True)
        society_id = data.get("society_id")
        exclude_grades = data.get("exclude_grades")
        if exclude_grades:
            if isinstance(exclude_grades, str):
                exclude_grades = [g.strip() for g in exclude_grades.split(",") if g.strip()]
            elif not isinstance(exclude_grades, list):
                exclude_grades = []
        else:
            exclude_grades = []
        # Role-based access control
        if user.is_staff:
            permitted_society_id = society_id
        elif hasattr(user, "managed_society") and user.managed_society is not None:
            if society_id is not None and int(society_id) != int(user.managed_society.id):
                raise PermissionDenied("You are not authorized to access this society's data.")
            permitted_society_id = user.managed_society.id
        else:
            farmer_permits = PermitApplication.objects.filter(farmer=user)
            farmer_society_ids = set(farmer_permits.values_list("society_id", flat=True))
            if society_id is not None and int(society_id) not in farmer_society_ids:
                raise PermissionDenied("You are not authorized to access this society's data.")
            permitted_society_id = list(farmer_society_ids) if society_id is None else [int(society_id)]
        permits = PermitApplication.objects.all()
        if start_date:
            permits = permits.filter(application_date__date__gte=start_date)
        if end_date:
            permits = permits.filter(application_date__date__lte=end_date)
        if user.is_staff:
            if permitted_society_id:
                permits = permits.filter(society_id=permitted_society_id)
        elif hasattr(user, "managed_society") and user.managed_society is not None:
            permits = permits.filter(society_id=permitted_society_id)
        else:
            permits = permits.filter(society_id__in=permitted_society_id, farmer=user)
        # --- Total Coffee Moved (by period and grade) ---
        total_coffee = []
        all_grades = list(CoffeeGrade.objects.values_list("grade", flat=True))
        if include_total:
            from .models import CoffeeQuantity
            # Choose truncation function based on granularity
            if granularity == "weekly":
                trunc_func = TruncWeek("application__application_date")
            elif granularity == "monthly":
                trunc_func = TruncMonth("application__application_date")
            elif granularity == "90days":
                trunc_func = TruncQuarter("application__application_date")
            else:
                trunc_func = TruncDay("application__application_date")

            coffee_quantities = CoffeeQuantity.objects.filter(application__in=permits)
            if exclude_grades:
                coffee_quantities = coffee_quantities.exclude(coffee_grade__grade__in=exclude_grades)
            grouped = (
                coffee_quantities
                .annotate(period=trunc_func)
                .values("period", "coffee_grade__grade")
                .annotate(total_weight=Sum(F("bags_quantity") * F("coffee_grade__weight_per_bag"), output_field=FloatField()))
                .order_by("period")
            )
            # Pivot to {period: {grade1: total, grade2: total, ...}}
            result = {}
            for row in grouped:
                if granularity == "daily":
                    period = row["period"].strftime("%Y-%m-%d")
                elif granularity == "weekly":
                    period = f"{row['period'].isocalendar()[0]}-W{row['period'].isocalendar()[1]:02d}"
                elif granularity == "monthly":
                    period = row["period"].strftime("%Y-%m")
                elif granularity == "90days":
                    period = f"{row['period'].year}-Q{((row['period'].month - 1) // 3) + 1}"
                else:
                    period = str(row["period"])
                if period not in result:
                    result[period] = {}
                result[period][row["coffee_grade__grade"]] = row["total_weight"]
            # Format for template
            for period in sorted(result.keys()):
                entry = {"period": period}
                for grade in all_grades:
                    entry[grade] = result[period].get(grade, 0)
                total_coffee.append(entry)

        # --- Top Factories ---
        top_factories = []
        if include_top_factories:
            from .models import CoffeeQuantity
            coffee_quantities = CoffeeQuantity.objects.filter(application__in=permits)
            grouped = (
                coffee_quantities
                .values("application__factory__id", "application__factory__name")
                .annotate(total_kg=Sum(F("bags_quantity") * F("coffee_grade__weight_per_bag"), output_field=FloatField()))
                .order_by("-total_kg")
            )
            top_factories = [
                {
                    "factory_id": row["application__factory__id"],
                    "factory": row["application__factory__name"],
                    "totalKg": row["total_kg"] or 0,
                }
                for row in grouped
            ]

        # --- Top Societies ---
        top_societies = []
        if include_top_societies:
            from .models import CoffeeQuantity
            coffee_quantities = CoffeeQuantity.objects.filter(application__in=permits)
            grouped = (
                coffee_quantities
                .values("application__society__id", "application__society__name")
                .annotate(total_kg=Sum(F("bags_quantity") * F("coffee_grade__weight_per_bag"), output_field=FloatField()))
                .order_by("-total_kg")
            )
            top_societies = [
                {
                    "society_id": row["application__society__id"],
                    "society": row["application__society__name"],
                    "totalKg": row["total_kg"] or 0,
                }
                for row in grouped
            ]

        # --- Top Grades (for society) ---
        top_grades = []
        if include_top_grades:
            from .models import CoffeeQuantity
            coffee_quantities = CoffeeQuantity.objects.filter(application__in=permits)
            grouped = (
                coffee_quantities
                .values("coffee_grade__grade")
                .annotate(total_kg=Sum(F("bags_quantity") * F("coffee_grade__weight_per_bag"), output_field=FloatField()))
                .order_by("-total_kg")
            )
            top_grades = [
                {
                    "grade": row["coffee_grade__grade"],
                    "totalKg": row["total_kg"] or 0,
                }
                for row in grouped
            ]

        # Get society name if relevant
        society_name = None
        if society_id:
            from societies.models import Society
            society = Society.objects.filter(id=society_id).first()
            if society:
                society_name = society.name

        # Render HTML template
        html_string = render_to_string(
            "permits/analytics_report_pdf.html",
            {
                "generation_date": datetime.datetime.now(),
                "start_date": start_date,
                "end_date": end_date,
                "granularity": granularity,
                "society_name": society_name,
                "top_factories": top_factories,
                "top_societies": top_societies,
                "top_grades": top_grades,
                "total_coffee": total_coffee,
                "all_grades": all_grades,
            },
        )
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="analytics_report.pdf"'
        pisa_status = pisa.CreatePDF(html_string, dest=response)
        if pisa_status.err:
            return HttpResponse("Error generating analytics report PDF", status=500)
        return response
    except Exception as e:
        return HttpResponse("Error generating analytics report PDF", status=500)
