from django.contrib import admin

from .models import Emission, TrafficStatistic


@admin.register(Emission)
class EmissionAdmin(admin.ModelAdmin):
    list_display = ('intersection', 'carbon_emission_kg', 'fuel_consumption_liters', 'pollution_index', 'window_start')
    list_filter = ('intersection',)
    date_hierarchy = 'window_start'
    ordering = ('-window_start',)


@admin.register(TrafficStatistic)
class TrafficStatisticAdmin(admin.ModelAdmin):
    list_display = ('intersection', 'period', 'period_start', 'total_vehicles', 'avg_congestion_score', 'peak_hour')
    list_filter = ('period', 'intersection')
    ordering = ('-period_start',)
