from django.contrib import admin
from .models import Intersection, Camera, Vehicle

@admin.register(Intersection)
class IntersectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'latitude', 'longitude')
    search_fields = ('name', 'location')

@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ('id', 'intersection', 'status')
    list_filter = ('status', 'intersection')

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_type', 'camera', 'confidence_score', 'timestamp')
    list_filter = ('vehicle_type', 'timestamp')
    search_fields = ('vehicle_type',)
    ordering = ('-timestamp',)
