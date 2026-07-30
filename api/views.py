from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from accounts.models import User
from monitoring.models import Intersection, Camera, Vehicle
from signals.models import Signal
from analytics.models import Emission
from .serializers import (UserSerializer, IntersectionSerializer, CameraSerializer, 
                          VehicleSerializer, SignalSerializer, EmissionSerializer)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class IntersectionViewSet(viewsets.ModelViewSet):
    queryset = Intersection.objects.all()
    serializer_class = IntersectionSerializer
    permission_classes = [IsAuthenticated]

class CameraViewSet(viewsets.ModelViewSet):
    queryset = Camera.objects.all()
    serializer_class = CameraSerializer
    permission_classes = [IsAuthenticated]

class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]

class SignalViewSet(viewsets.ModelViewSet):
    queryset = Signal.objects.all()
    serializer_class = SignalSerializer
    permission_classes = [IsAuthenticated]

class EmissionViewSet(viewsets.ModelViewSet):
    queryset = Emission.objects.all()
    serializer_class = EmissionSerializer
    permission_classes = [IsAuthenticated]
