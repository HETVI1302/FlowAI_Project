from django.db import models
from monitoring.models import Intersection

class Emission(models.Model):
    intersection = models.ForeignKey(Intersection, on_delete=models.CASCADE, related_name='emissions')
    carbon_emission = models.FloatField(help_text="Estimated carbon emission in grams")
    fuel_consumption = models.FloatField(help_text="Estimated fuel consumption in liters")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Emission stats at {self.intersection.name} on {self.timestamp}"
