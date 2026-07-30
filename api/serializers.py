from rest_framework import serializers
from accounts.models import User
from monitoring.models import Intersection, Camera, Vehicle
from signals.models import Signal
from analytics.models import Emission

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'role', 'created_at']

class IntersectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intersection
        fields = '__all__'

class CameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera
        fields = '__all__'

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class SignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signal
        fields = '__all__'

class EmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Emission
        fields = '__all__'
