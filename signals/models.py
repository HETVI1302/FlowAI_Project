from django.db import models
from monitoring.models import Intersection

class Signal(models.Model):
    intersection = models.OneToOneField(Intersection, on_delete=models.CASCADE, related_name='signal')
    green_time = models.IntegerField(default=30, help_text="Time in seconds")
    yellow_time = models.IntegerField(default=5, help_text="Time in seconds")
    red_time = models.IntegerField(default=30, help_text="Time in seconds")
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Signal at {self.intersection.name}"
