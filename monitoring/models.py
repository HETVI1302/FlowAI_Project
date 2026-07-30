import uuid

from django.db import models


class Intersection(models.Model):
    """A physical road intersection / junction being monitored."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'
        MAINTENANCE = 'maintenance', 'Under Maintenance'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=255, help_text='Human-readable address / area')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'intersections'
        ordering = ['name']
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return self.name


class Camera(models.Model):
    """A CCTV camera feed attached to an intersection."""

    class Status(models.TextChoices):
        ONLINE = 'online', 'Online'
        OFFLINE = 'offline', 'Offline'
        ERROR = 'error', 'Error'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intersection = models.ForeignKey(
        Intersection, on_delete=models.CASCADE, related_name='cameras'
    )
    name = models.CharField(max_length=100, blank=True)
    camera_url = models.CharField(
        max_length=500, help_text='RTSP/HTTP stream URL consumed by the CV worker'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OFFLINE)
    resolution = models.CharField(max_length=20, blank=True, help_text='e.g. 1920x1080')
    fps = models.PositiveSmallIntegerField(default=15)
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cameras'
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return f'{self.name or "Camera"} @ {self.intersection.name}'


class Vehicle(models.Model):
    """
    A single vehicle detection event produced by the YOLOv8 worker for a
    given camera frame. One row per detected vehicle, not per frame —
    keeps this table append-only and cheap to aggregate for dashboards.
    """

    class VehicleType(models.TextChoices):
        CAR = 'car', 'Car'
        BUS = 'bus', 'Bus'
        TRUCK = 'truck', 'Truck'
        MOTORCYCLE = 'motorcycle', 'Motorcycle'
        AMBULANCE = 'ambulance', 'Ambulance'
        POLICE = 'police', 'Police Vehicle'
        OTHER = 'other', 'Other'

    id = models.BigAutoField(primary_key=True)
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='vehicle_detections')
    intersection = models.ForeignKey(
        Intersection, on_delete=models.CASCADE, related_name='vehicle_detections'
    )
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices)
    confidence_score = models.FloatField(help_text='YOLOv8 detection confidence, 0-1')
    is_emergency = models.BooleanField(default=False)
    bounding_box = models.JSONField(
        null=True, blank=True, help_text='[x_min, y_min, x_max, y_max] in frame pixels'
    )
    speed_kmph = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'vehicles'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['intersection', 'timestamp']),
            models.Index(fields=['vehicle_type']),
            models.Index(fields=['is_emergency']),
        ]

    def __str__(self):
        return f'{self.vehicle_type} @ {self.timestamp:%Y-%m-%d %H:%M:%S}'

    def save(self, *args, **kwargs):
        # Emergency vehicles get flagged automatically so downstream
        # consumers (signal prioritization, alerts) don't have to
        # re-derive it from vehicle_type every time.
        self.is_emergency = self.vehicle_type in (
            self.VehicleType.AMBULANCE, self.VehicleType.POLICE
        )
        super().save(*args, **kwargs)


class TrafficDensitySnapshot(models.Model):
    """
    Periodic rollup (e.g. every 60s) of queue length / density per
    intersection, computed from the raw Vehicle detections. Backs the
    congestion-level cards and charts without re-aggregating millions
    of Vehicle rows on every dashboard refresh.
    """

    class CongestionLevel(models.TextChoices):
        LOW = 'low', 'Low'
        MODERATE = 'moderate', 'Moderate'
        HIGH = 'high', 'High'
        SEVERE = 'severe', 'Severe'

    id = models.BigAutoField(primary_key=True)
    intersection = models.ForeignKey(
        Intersection, on_delete=models.CASCADE, related_name='density_snapshots'
    )
    vehicle_count = models.PositiveIntegerField(default=0)
    queue_length_meters = models.FloatField(default=0)
    avg_waiting_time_seconds = models.FloatField(default=0)
    congestion_level = models.CharField(
        max_length=20, choices=CongestionLevel.choices, default=CongestionLevel.LOW
    )
    captured_at = models.DateTimeField(db_index=True)

    class Meta:
        db_table = 'traffic_density_snapshots'
        ordering = ['-captured_at']
        indexes = [models.Index(fields=['intersection', 'captured_at'])]

    def __str__(self):
        return f'{self.intersection.name} — {self.congestion_level} @ {self.captured_at:%H:%M}'
