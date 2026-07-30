import uuid

from django.conf import settings
from django.db import models

from monitoring.models import Intersection


class Report(models.Model):
    """A generated analytics report (daily/weekly/monthly) available for
    download from the Analytics module."""

    class ReportType(models.TextChoices):
        DAILY = 'daily', 'Daily Report'
        WEEKLY = 'weekly', 'Weekly Report'
        MONTHLY = 'monthly', 'Monthly Report'
        CUSTOM = 'custom', 'Custom Range'

    class Format(models.TextChoices):
        PDF = 'pdf', 'PDF'
        CSV = 'csv', 'CSV'
        XLSX = 'xlsx', 'Excel'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        GENERATING = 'generating', 'Generating'
        READY = 'ready', 'Ready'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intersection = models.ForeignKey(
        Intersection, on_delete=models.CASCADE, null=True, blank=True,
        related_name='reports', help_text='Null = city-wide report'
    )
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='reports'
    )
    report_type = models.CharField(max_length=10, choices=ReportType.choices)
    file_format = models.CharField(max_length=10, choices=Format.choices, default=Format.PDF)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    period_start = models.DateField()
    period_end = models.DateField()
    file = models.FileField(upload_to='reports/%Y/%m/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status']), models.Index(fields=['report_type'])]

    def __str__(self):
        return f'{self.get_report_type_display()} ({self.period_start} → {self.period_end})'
