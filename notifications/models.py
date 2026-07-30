from django.db import models
from accounts.models import User

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('congestion', 'Traffic Congestion'),
        ('accident', 'Accident'),
        ('signal_failure', 'Signal Failure'),
        ('emergency', 'Emergency Alert'),
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)

    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.title}"
