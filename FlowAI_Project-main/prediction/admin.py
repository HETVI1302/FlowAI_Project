from django.contrib import admin

from .models import CongestionPrediction, IncidentDetection, TrafficPattern


@admin.register(CongestionPrediction)
class CongestionPredictionAdmin(admin.ModelAdmin):
    list_display = ('intersection', 'predicted_for', 'predicted_level', 'predicted_vehicle_count', 'confidence', 'model_version')
    list_filter = ('predicted_level', 'model_version')
    date_hierarchy = 'predicted_for'


@admin.register(IncidentDetection)
class IncidentDetectionAdmin(admin.ModelAdmin):
    list_display = ('intersection', 'incident_type', 'severity', 'confidence', 'is_resolved', 'detected_at')
    list_filter = ('incident_type', 'severity', 'is_resolved')
    date_hierarchy = 'detected_at'


@admin.register(TrafficPattern)
class TrafficPatternAdmin(admin.ModelAdmin):
    list_display = ('intersection', 'day_of_week', 'hour_of_day', 'avg_vehicle_count', 'avg_congestion_score', 'sample_size')
    list_filter = ('day_of_week',)
    search_fields = ('intersection__name',)
