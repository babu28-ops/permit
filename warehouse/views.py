from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from .models import Warehouse
from .serializers import WarehouseSerializer
from rest_framework.decorators import action


class WarehouseViewSet(viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer
    queryset = Warehouse.objects.all() # Fetch warehouse DB

    def get_permissions(self):
        """
        List and retrieve operations are allowed for authenticated users,
        while create, update, and delete operations are restricted to admin users.
        The active_warehouses action is also allowed for authenticated users.
        """
        if self.action in ['list', 'retrieve', 'active_warehouses']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['get'])
    def active_warehouses(self, request):
        """Get only active warehouses for permit applications"""
        queryset = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
