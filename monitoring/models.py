from django.db import models

class Intersection(models.Model):
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    location = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Camera(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
    )
    intersection = models.ForeignKey(Intersection, on_delete=models.CASCADE, related_name='cameras')
    camera_url = models.URLField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"Camera {self.id} at {self.intersection.name}"

class Vehicle(models.Model):
    VEHICLE_TYPES = (
        ('car', 'Car'),
        ('bus', 'Bus'),
        ('truck', 'Truck'),
        ('motorcycle', 'Motorcycle'),
        ('ambulance', 'Ambulance'),
        ('police', 'Police Vehicle'),
    )
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='detected_vehicles', null=True, blank=True)
    vehicle_type = models.CharField(max_length=50, choices=VEHICLE_TYPES)
    confidence_score = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.vehicle_type} detected at {self.timestamp}"
