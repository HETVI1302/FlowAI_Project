import uuid

from django.db import models

from monitoring.models import Intersection


class Signal(models.Model):
    """
    Current timing configuration for a traffic signal at an intersection.
    `is_dynamic` marks whether the AI optimizer is allowed to adjust the
    timings live, or whether it's pinned to a fixed manual schedule.
    """

    class Mode(models.TextChoices):
        FIXED = 'fixed', 'Fixed Timing'
        DYNAMIC = 'dynamic', 'AI-Optimized'
        MANUAL = 'manual', 'Manual Override'
        EMERGENCY = 'emergency', 'Emergency Priority'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intersection = models.OneToOneField(
        Intersection, on_delete=models.CASCADE, related_name='signal'
    )
    green_time = models.PositiveSmallIntegerField(help_text='seconds')
    yellow_time = models.PositiveSmallIntegerField(default=3, help_text='seconds')
    red_time = models.PositiveSmallIntegerField(help_text='seconds')
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.FIXED)
    is_active = models.BooleanField(default=True)
    last_updated_by = models.CharField(
        max_length=50, default='system', help_text="'system' (AI) or operator username"
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'signals'

    def __str__(self):
        return f'Signal @ {self.intersection.name} ({self.mode})'

    @property
    def cycle_length(self):
        return self.green_time + self.yellow_time + self.red_time


class SignalChangeLog(models.Model):
    """
    Audit trail of every timing change applied to a signal — whether
    triggered by the AI optimizer, an emergency override, or a manual
    operator edit. Needed for the "automated traffic control" feature
    to be explainable/auditable rather than a black box.
    """
    id = models.BigAutoField(primary_key=True)
    signal = models.ForeignKey(Signal, on_delete=models.CASCADE, related_name='change_logs')
    previous_green_time = models.PositiveSmallIntegerField()
    new_green_time = models.PositiveSmallIntegerField()
    reason = models.CharField(max_length=255, blank=True)
    triggered_by = models.CharField(max_length=50, default='system')
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'signal_change_logs'
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.signal.intersection.name} {self.previous_green_time}s→{self.new_green_time}s'
