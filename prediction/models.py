import uuid

from django.db import models

from monitoring.models import Intersection


class CongestionPrediction(models.Model):
    """Forward-looking congestion forecast for an intersection, produced
    by the prediction model (e.g. an LSTM/time-series model over the
    TrafficDensitySnapshot history)."""

    class CongestionLevel(models.TextChoices):
        LOW = 'low', 'Low'
        MODERATE = 'moderate', 'Moderate'
        HIGH = 'high', 'High'
        SEVERE = 'severe', 'Severe'

    id = models.BigAutoField(primary_key=True)
    intersection = models.ForeignKey(
        Intersection, on_delete=models.CASCADE, related_name='congestion_predictions'
    )
    predicted_for = models.DateTimeField(help_text='Timestamp this prediction is forecasting')
    predicted_level = models.CharField(max_length=20, choices=CongestionLevel.choices)
    predicted_vehicle_count = models.PositiveIntegerField(null=True, blank=True)
    confidence = models.FloatField(help_text='Model confidence, 0-1')
    model_version = models.CharField(max_length=50, default='v1')
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'congestion_predictions'
        ordering = ['-predicted_for']
        indexes = [models.Index(fields=['intersection', 'predicted_for'])]

    def __str__(self):
        return f'{self.intersection.name} → {self.predicted_level} @ {self.predicted_for:%H:%M}'


class IncidentDetection(models.Model):
    """Accident / anomaly detected by the CV pipeline (stalled vehicle,
    collision, debris, wrong-way driver, etc.)."""

    class IncidentType(models.TextChoices):
        ACCIDENT = 'accident', 'Accident'
        STALLED_VEHICLE = 'stalled_vehicle', 'Stalled Vehicle'
        WRONG_WAY = 'wrong_way', 'Wrong-Way Driver'
        OBSTRUCTION = 'obstruction', 'Road Obstruction'
        OTHER = 'other', 'Other Anomaly'

    class Severity(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        CRITICAL = 'critical', 'Critical'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intersection = models.ForeignKey(
        Intersection, on_delete=models.CASCADE, related_name='incidents'
    )
    camera = models.ForeignKey(
        'monitoring.Camera', on_delete=models.SET_NULL, null=True, related_name='incidents'
    )
    incident_type = models.CharField(max_length=30, choices=IncidentType.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    confidence = models.FloatField()
    snapshot_image = models.ImageField(upload_to='incidents/%Y/%m/%d/', null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    detected_at = models.DateTimeField(db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'incident_detections'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['intersection', 'detected_at']),
            models.Index(fields=['is_resolved']),
        ]

    def __str__(self):
        return f'{self.incident_type} @ {self.intersection.name} ({self.severity})'


class TrafficPattern(models.Model):
    """Recurring traffic pattern learned for an intersection (e.g. 'heavy
    inbound weekday mornings'), used to explain/inform predictions."""

    id = models.BigAutoField(primary_key=True)
    intersection = models.ForeignKey(
        Intersection, on_delete=models.CASCADE, related_name='patterns'
    )
    day_of_week = models.PositiveSmallIntegerField(help_text='0=Monday .. 6=Sunday')
    hour_of_day = models.PositiveSmallIntegerField(help_text='0-23')
    avg_vehicle_count = models.FloatField(default=0)
    avg_congestion_score = models.FloatField(default=0)
    sample_size = models.PositiveIntegerField(default=0, help_text='# of days this pattern is averaged over')
    last_computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'traffic_patterns'
        unique_together = ('intersection', 'day_of_week', 'hour_of_day')
        indexes = [models.Index(fields=['intersection', 'day_of_week', 'hour_of_day'])]

    def __str__(self):
        return f'{self.intersection.name} — day {self.day_of_week} hr {self.hour_of_day}'
