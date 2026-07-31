from django.db import models

from monitoring.models import Intersection


class Emission(models.Model):
    """
    Environmental-impact estimate for an intersection over a time
    window, derived from vehicle counts/types and idle time. Powers the
    Environmental Monitoring module (fuel consumption, carbon emission,
    pollution level).
    """
    id = models.BigAutoField(primary_key=True)
    intersection = models.ForeignKey(
        Intersection, on_delete=models.CASCADE, related_name='emissions'
    )
    carbon_emission_kg = models.FloatField(help_text='Estimated CO2 in kilograms')
    fuel_consumption_liters = models.FloatField(help_text='Estimated fuel burned in liters')
    pollution_index = models.FloatField(
        null=True, blank=True, help_text='Composite air-quality proxy score'
    )
    idle_time_seconds = models.FloatField(default=0, help_text='Aggregate vehicle idle time')
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'emissions'
        ordering = ['-window_start']
        indexes = [models.Index(fields=['intersection', 'window_start'])]

    def __str__(self):
        return f'{self.intersection.name} — {self.carbon_emission_kg:.1f}kg CO2'


class TrafficStatistic(models.Model):
    """
    Daily/weekly/monthly rollup used to render the Chart.js analytics
    dashboards without recomputing from raw detections each request.
    """

    class Period(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'

    id = models.BigAutoField(primary_key=True)
    intersection = models.ForeignKey(
        Intersection, on_delete=models.CASCADE, related_name='statistics'
    )
    period = models.CharField(max_length=10, choices=Period.choices)
    period_start = models.DateField()
    total_vehicles = models.PositiveIntegerField(default=0)
    avg_congestion_score = models.FloatField(default=0)
    avg_waiting_time_seconds = models.FloatField(default=0)
    peak_hour = models.PositiveSmallIntegerField(null=True, blank=True, help_text='0-23')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'traffic_statistics'
        ordering = ['-period_start']
        unique_together = ('intersection', 'period', 'period_start')
        indexes = [models.Index(fields=['intersection', 'period', 'period_start'])]

    def __str__(self):
        return f'{self.intersection.name} {self.period} {self.period_start}'
