from django.contrib import admin

from .models import Camera, Intersection, TrafficDensitySnapshot, Vehicle


@admin.register(Intersection)
class IntersectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'status', 'updated_at')
    list_filter = ('status',)
    search_fields = ('name', 'location')


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ('name', 'intersection', 'status', 'fps', 'last_heartbeat')
    list_filter = ('status',)
    search_fields = ('name', 'camera_url', 'intersection__name')
    autocomplete_fields = ('intersection',)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_type', 'intersection', 'camera', 'confidence_score', 'is_emergency', 'timestamp')
    list_filter = ('vehicle_type', 'is_emergency')
    date_hierarchy = 'timestamp'
    readonly_fields = ('is_emergency',)


@admin.register(TrafficDensitySnapshot)
class TrafficDensitySnapshotAdmin(admin.ModelAdmin):
    list_display = ('intersection', 'vehicle_count', 'congestion_level', 'avg_waiting_time_seconds', 'captured_at')
    list_filter = ('congestion_level',)
    date_hierarchy = 'captured_at'
