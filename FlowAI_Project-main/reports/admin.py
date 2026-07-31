from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'intersection', 'file_format', 'status', 'period_start', 'period_end', 'created_at')
    list_filter = ('status', 'report_type', 'file_format')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'completed_at')
