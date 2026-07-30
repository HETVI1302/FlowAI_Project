from django.contrib import admin
from .models import Emission

@admin.register(Emission)
class EmissionAdmin(admin.ModelAdmin):
    list_display = ('intersection', 'carbon_emission', 'fuel_consumption', 'timestamp')
    list_filter = ('intersection', 'timestamp')
    ordering = ('-timestamp',)
