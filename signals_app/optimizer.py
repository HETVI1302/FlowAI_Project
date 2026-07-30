"""
Signal Management module. Two entry points, both plain sync functions so they
can be called from anywhere sync (the CV worker process, a management-command
loop, or a Django view) without an event loop of their own — same
async_to_sync bridge monitoring/cv/pipeline.py uses to reach the channel layer.

  * optimize_signal(intersection)        — called periodically (see the
    run_signal_optimizer command) for every intersection whose Signal is in
    DYNAMIC mode. Maps the latest TrafficDensitySnapshot's congestion level
    to a green-time band and applies it, logging the change.

  * trigger_emergency_priority(...)      — called the instant the CV worker
    detects an ambulance/police vehicle (see monitoring/cv/pipeline.py's
    _broadcast_emergency, extended in this phase). Forces the signal green
    immediately and flips it into EMERGENCY mode; run_signal_optimizer's loop
    is responsible for reverting it after EMERGENCY_HOLD_SECONDS once the
    vehicle has had time to clear the intersection.

Both paths write a SignalChangeLog row so every timing change — AI-driven or
emergency override — is auditable, per the "automated traffic control"
requirement.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from monitoring.models import TrafficDensitySnapshot
from notifications.services import notify
from notifications.models import Notification

from .consumers import SIGNALS_GROUP
from .models import Signal, SignalChangeLog

logger = logging.getLogger('signals_app.optimizer')

# Congestion level -> green-time band (seconds). Wider band than the fixed
# default so the optimizer has room to actually respond to the CV feed.
GREEN_TIME_BY_CONGESTION = {
    TrafficDensitySnapshot.CongestionLevel.LOW: 20,
    TrafficDensitySnapshot.CongestionLevel.MODERATE: 35,
    TrafficDensitySnapshot.CongestionLevel.HIGH: 55,
    TrafficDensitySnapshot.CongestionLevel.SEVERE: 75,
}
MIN_GREEN_TIME = 15
MAX_GREEN_TIME = 90

EMERGENCY_GREEN_TIME = 90
EMERGENCY_HOLD_SECONDS = 45  # how long a signal stays pinned to EMERGENCY mode


def optimize_signal(intersection):
    """Re-evaluate one intersection's signal against its latest snapshot.
    No-op if the signal isn't in DYNAMIC mode (manual/emergency overrides
    are left alone) or if there's no snapshot yet."""
    try:
        signal = Signal.objects.select_related('intersection').get(
            intersection=intersection, is_active=True, mode=Signal.Mode.DYNAMIC
        )
    except Signal.DoesNotExist:
        return None

    snapshot = (
        TrafficDensitySnapshot.objects.filter(intersection=intersection)
        .order_by('-captured_at').first()
    )
    if snapshot is None:
        return None

    target_green = GREEN_TIME_BY_CONGESTION.get(snapshot.congestion_level, signal.green_time)
    target_green = max(MIN_GREEN_TIME, min(MAX_GREEN_TIME, target_green))

    if target_green == signal.green_time:
        return signal  # already at the right timing, nothing to log/broadcast

    previous_green = signal.green_time
    signal.green_time = target_green
    signal.red_time = max(MIN_GREEN_TIME, target_green + signal.yellow_time)
    signal.last_updated_by = 'system'
    signal.save(update_fields=['green_time', 'red_time', 'last_updated_by', 'updated_at'])

    SignalChangeLog.objects.create(
        signal=signal,
        previous_green_time=previous_green,
        new_green_time=target_green,
        reason=f'AI optimizer: congestion={snapshot.congestion_level}, vehicles={snapshot.vehicle_count}',
        triggered_by='system',
    )
    _broadcast_signal_update(signal, reason='ai_optimized')
    return signal


def trigger_emergency_priority(intersection, vehicle_type):
    """Force green + EMERGENCY mode the instant an ambulance/police vehicle
    is detected approaching this intersection. Idempotent-ish: re-triggering
    while already in EMERGENCY mode just refreshes the hold window (via
    updated_at) rather than double-logging."""
    try:
        signal = Signal.objects.select_related('intersection').get(
            intersection=intersection, is_active=True
        )
    except Signal.DoesNotExist:
        logger.warning('Emergency priority requested but no Signal exists for %s', intersection)
        return None

    already_emergency = signal.mode == Signal.Mode.EMERGENCY
    previous_green = signal.green_time
    previous_mode = signal.mode

    signal.green_time = EMERGENCY_GREEN_TIME
    signal.mode = Signal.Mode.EMERGENCY
    signal.last_updated_by = 'system'
    signal.save(update_fields=['green_time', 'mode', 'last_updated_by', 'updated_at'])

    if not already_emergency:
        SignalChangeLog.objects.create(
            signal=signal,
            previous_green_time=previous_green,
            new_green_time=EMERGENCY_GREEN_TIME,
            reason=f'Emergency priority: {vehicle_type} approaching',
            triggered_by='system',
        )
        notify(
            category=Notification.Category.EMERGENCY_VEHICLE,
            priority=Notification.Priority.CRITICAL,
            title='Emergency vehicle priority activated',
            message=f'{vehicle_type.title()} detected near {signal.intersection.name} — signal forced green.',
            intersection=signal.intersection,
        )

    # Stash the mode to revert to once the hold window elapses (only on the
    # initial trigger — re-triggers while already emergency shouldn't
    # overwrite it with EMERGENCY itself).
    _pending_revert_mode(signal, previous_mode if not already_emergency else None)

    _broadcast_signal_update(signal, reason='emergency_priority', extra={'emergency': True, 'vehicle_type': vehicle_type})
    return signal


# In-process cache of "what mode to revert each emergency signal to" — good
# enough for a single-worker hackathon deployment. A multi-process deployment
# would move this onto the Signal row (e.g. a `pre_emergency_mode` field) so
# any worker's revert pass can see it.
_REVERT_MODES = {}


def _pending_revert_mode(signal, mode):
    if mode is not None:
        _REVERT_MODES[str(signal.pk)] = mode


def revert_expired_emergencies():
    """Called from run_signal_optimizer's loop: any signal that's been sat in
    EMERGENCY mode longer than EMERGENCY_HOLD_SECONDS goes back to whatever
    mode it was in before (defaulting to DYNAMIC if we don't have a record,
    e.g. after a process restart)."""
    cutoff = timezone.now() - timezone.timedelta(seconds=EMERGENCY_HOLD_SECONDS)
    expired = Signal.objects.filter(mode=Signal.Mode.EMERGENCY, updated_at__lte=cutoff)
    for signal in expired:
        revert_mode = _REVERT_MODES.pop(str(signal.pk), Signal.Mode.DYNAMIC)
        previous_green = signal.green_time
        signal.mode = revert_mode
        signal.last_updated_by = 'system'
        signal.save(update_fields=['mode', 'last_updated_by', 'updated_at'])
        SignalChangeLog.objects.create(
            signal=signal,
            previous_green_time=previous_green,
            new_green_time=signal.green_time,
            reason=f'Emergency hold expired, reverted to {revert_mode}',
            triggered_by='system',
        )
        _broadcast_signal_update(signal, reason='emergency_expired')


def _broadcast_signal_update(signal, reason, extra=None):
    payload = {
        'type': 'signal.update',
        'signal_id': str(signal.id),
        'intersection_id': str(signal.intersection_id),
        'intersection_name': signal.intersection.name,
        'mode': signal.mode,
        'green_time': signal.green_time,
        'yellow_time': signal.yellow_time,
        'red_time': signal.red_time,
        'reason': reason,
        'updated_at': timezone.now().isoformat(),
    }
    if extra:
        payload.update(extra)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(SIGNALS_GROUP, {
        'type': 'signal_update',
        'payload': payload,
    })
