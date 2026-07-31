from django.conf import settings
from django.db import models


class DashboardPreference(models.Model):
    """
    Per-user layout/preferences for the live dashboard — which cards are
    shown, default intersection filter, refresh interval, etc. Keeps the
    dashboard app owning UI state rather than mixing it into `accounts`.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='dashboard_preference'
    )
    visible_cards = models.JSONField(
        default=list,
        help_text="e.g. ['active_intersections','total_vehicles','congestion','emissions']"
    )
    default_intersection = models.ForeignKey(
        'monitoring.Intersection', on_delete=models.SET_NULL, null=True, blank=True
    )
    refresh_interval_seconds = models.PositiveSmallIntegerField(default=10)
    theme = models.CharField(max_length=20, default='dark')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dashboard_preferences'

    def __str__(self):
        return f'Dashboard prefs — {self.user}'
