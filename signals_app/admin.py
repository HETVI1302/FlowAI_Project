from django.contrib import admin

from .models import Signal, SignalChangeLog


@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ('intersection', 'mode', 'green_time', 'yellow_time', 'red_time', 'is_active', 'updated_at')
    list_filter = ('mode', 'is_active')
    search_fields = ('intersection__name',)
    autocomplete_fields = ('intersection',)


@admin.register(SignalChangeLog)
class SignalChangeLogAdmin(admin.ModelAdmin):
    list_display = ('signal', 'previous_green_time', 'new_green_time', 'triggered_by', 'changed_at')
    list_filter = ('triggered_by',)
    date_hierarchy = 'changed_at'
