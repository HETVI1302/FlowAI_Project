from django.contrib import admin
from .models import Signal

@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ('intersection', 'green_time', 'yellow_time', 'red_time', 'is_active', 'last_updated')
    list_filter = ('is_active', 'intersection')
