"""
AI Prediction module. Three responsibilities, meant to be called
periodically per-intersection (see run_prediction_engine):

  * build_traffic_patterns(intersection) — rolls up TrafficDensitySnapshot
    history into TrafficPattern rows (avg vehicle count / congestion score
    per day-of-week + hour-of-day), updated incrementally so re-running it
    doesn't double-count. Everything else in this file reads from these
    patterns rather than raw snapshots, so a slow-changing baseline is
    always available even if the CV feed is currently degraded.

  * generate_forecasts(intersection) — for each horizon in FORECAST_HORIZONS
    (minutes), looks up the TrafficPattern for that future day/hour and
    turns its historical average into a CongestionPrediction. Confidence
    scales with TrafficPattern.sample_size — a forecast built from one
    day of history is explicitly flagged low-confidence rather than
    pretending to a precision it doesn't have. Falls back to "whatever the
    congestion level is right now, held steady" when no pattern exists yet
    (e.g. a brand-new intersection).

  * detect_anomalies(intersection) — compares the *current* snapshot
    against the TrafficPattern baseline for this exact day/hour; a
    sustained deviation well outside the normal range gets logged as an
    IncidentDetection. This is a statistical anomaly detector, not a
    learned accident classifier — it can tell "this is unusually congested
    for a Tuesday at 9am" but not *why* (accident vs. a parade vs. a lane
    closure), so detections are raised as IncidentType.OTHER at moderate
    confidence rather than over-claiming. Swap in a trained
    accident-detection model without touching the rest of this file once
    labeled training data exists.
"""
import logging
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from monitoring.models import TrafficDensitySnapshot
from notifications.models import Notification
from notifications.services import notify

from .consumers import PREDICTION_GROUP
from .models import CongestionPrediction, IncidentDetection, TrafficPattern

logger = logging.getLogger('prediction.engine')

FORECAST_HORIZONS_MINUTES = (15, 30, 60)
PATTERN_LOOKBACK_DAYS = 30  # how far back to seed a pattern that has no cursor yet
MIN_SAMPLES_FOR_CONFIDENT_FORECAST = 5

# Congestion level <-> numeric score, so patterns can average across levels.
CONGESTION_SCORE = {
    TrafficDensitySnapshot.CongestionLevel.LOW: 1,
    TrafficDensitySnapshot.CongestionLevel.MODERATE: 2,
    TrafficDensitySnapshot.CongestionLevel.HIGH: 3,
    TrafficDensitySnapshot.CongestionLevel.SEVERE: 4,
}
SCORE_TO_LEVEL = {v: k for k, v in CONGESTION_SCORE.items()}

# Anomaly detection: how far above the historical baseline (as a fraction,
# e.g. 1.0 = double the normal count) counts as worth flagging, and how many
# samples the baseline needs before it's trusted enough to alert on.
ANOMALY_DEVIATION_THRESHOLD = 1.0
MIN_SAMPLES_FOR_ANOMALY_CHECK = 5
# Don't re-raise a new incident for the same intersection within this window
# if an unresolved one already exists — one open ticket per episode, not one
# per polling tick.
ANOMALY_DEDUPE_WINDOW_MINUTES = 20

# In-process watermark of "TrafficDensitySnapshot.captured_at we've already
# rolled into a pattern", keyed by intersection id. Good enough for a
# single-process hackathon deployment — same tradeoff as the emergency-mode
# cache in signals_app/optimizer.py; a multi-worker deployment would persist
# this instead (e.g. a `last_rolled_up_at` field on TrafficPattern/Intersection).
_LAST_PATTERN_CURSOR = {}


def build_traffic_patterns(intersection):
    """Incrementally folds any snapshots captured since the last run into
    the (day_of_week, hour_of_day) TrafficPattern buckets. Returns how many
    snapshots were processed."""
    since = _LAST_PATTERN_CURSOR.get(str(intersection.pk))
    queryset = TrafficDensitySnapshot.objects.filter(intersection=intersection)
    queryset = queryset.filter(captured_at__gt=since) if since else queryset.filter(
        captured_at__gte=timezone.now() - timedelta(days=PATTERN_LOOKBACK_DAYS)
    )
    snapshots = list(queryset.order_by('captured_at'))

    for snapshot in snapshots:
        local_time = timezone.localtime(snapshot.captured_at)
        congestion_score = CONGESTION_SCORE[snapshot.congestion_level]

        pattern, created = TrafficPattern.objects.get_or_create(
            intersection=intersection,
            day_of_week=local_time.weekday(),
            hour_of_day=local_time.hour,
            defaults={
                'avg_vehicle_count': snapshot.vehicle_count,
                'avg_congestion_score': congestion_score,
                'sample_size': 1,
            },
        )
        if not created:
            n = pattern.sample_size + 1
            # Incremental mean — avoids re-summing the whole history on every tick.
            pattern.avg_vehicle_count += (snapshot.vehicle_count - pattern.avg_vehicle_count) / n
            pattern.avg_congestion_score += (congestion_score - pattern.avg_congestion_score) / n
            pattern.sample_size = n
            pattern.save(update_fields=['avg_vehicle_count', 'avg_congestion_score', 'sample_size', 'last_computed_at'])

    if snapshots:
        _LAST_PATTERN_CURSOR[str(intersection.pk)] = snapshots[-1].captured_at
    return len(snapshots)


def generate_forecasts(intersection):
    """Writes one CongestionPrediction per FORECAST_HORIZONS_MINUTES entry
    and broadcasts them to the prediction overview socket."""
    now = timezone.now()
    latest_snapshot = (
        TrafficDensitySnapshot.objects.filter(intersection=intersection).order_by('-captured_at').first()
    )
    predictions = []

    for horizon in FORECAST_HORIZONS_MINUTES:
        target_time = now + timedelta(minutes=horizon)
        local_target = timezone.localtime(target_time)
        pattern = TrafficPattern.objects.filter(
            intersection=intersection, day_of_week=local_target.weekday(), hour_of_day=local_target.hour
        ).first()

        if pattern:
            predicted_level = SCORE_TO_LEVEL.get(round(pattern.avg_congestion_score), TrafficDensitySnapshot.CongestionLevel.MODERATE)
            predicted_vehicle_count = round(pattern.avg_vehicle_count)
            # Confidence climbs with sample size but never claims certainty;
            # caps at 0.9 since this baseline can't see one-off disruptions.
            confidence = min(0.9, 0.3 + 0.06 * pattern.sample_size) if pattern.sample_size >= MIN_SAMPLES_FOR_CONFIDENT_FORECAST else 0.35
        elif latest_snapshot:
            # No historical pattern yet for this slot — hold the current
            # reading steady rather than guessing, and say so via low confidence.
            predicted_level = latest_snapshot.congestion_level
            predicted_vehicle_count = latest_snapshot.vehicle_count
            confidence = 0.25
        else:
            continue  # nothing to forecast from at all yet

        prediction = CongestionPrediction.objects.create(
            intersection=intersection,
            predicted_for=target_time,
            predicted_level=predicted_level,
            predicted_vehicle_count=predicted_vehicle_count,
            confidence=round(confidence, 2),
            model_version='pattern-baseline-v1',
        )
        predictions.append(prediction)

    if predictions:
        _broadcast_forecast(intersection, predictions)
    return predictions


def detect_anomalies(intersection):
    """Flags the current snapshot as a possible incident if it's well
    outside the historical baseline for this exact day/hour. Returns the
    created IncidentDetection, or None if nothing was flagged (either
    because nothing's anomalous, there isn't enough history yet, or an
    unresolved incident for this intersection is already open)."""
    snapshot = (
        TrafficDensitySnapshot.objects.filter(intersection=intersection).order_by('-captured_at').first()
    )
    if snapshot is None:
        return None

    local_time = timezone.localtime(snapshot.captured_at)
    pattern = TrafficPattern.objects.filter(
        intersection=intersection, day_of_week=local_time.weekday(), hour_of_day=local_time.hour
    ).first()
    if pattern is None or pattern.sample_size < MIN_SAMPLES_FOR_ANOMALY_CHECK:
        return None  # baseline not trustworthy yet — don't cry wolf

    baseline = max(pattern.avg_vehicle_count, 1)
    deviation = (snapshot.vehicle_count - baseline) / baseline
    if deviation < ANOMALY_DEVIATION_THRESHOLD:
        return None

    dedupe_cutoff = timezone.now() - timedelta(minutes=ANOMALY_DEDUPE_WINDOW_MINUTES)
    already_open = IncidentDetection.objects.filter(
        intersection=intersection, is_resolved=False, detected_at__gte=dedupe_cutoff
    ).exists()
    if already_open:
        return None

    severity = (
        IncidentDetection.Severity.CRITICAL if deviation >= 2.0 else
        IncidentDetection.Severity.HIGH if deviation >= 1.5 else
        IncidentDetection.Severity.MEDIUM
    )
    confidence = min(0.85, 0.4 + deviation * 0.15)

    incident = IncidentDetection.objects.create(
        intersection=intersection,
        incident_type=IncidentDetection.IncidentType.OTHER,
        severity=severity,
        confidence=round(confidence, 2),
        detected_at=snapshot.captured_at,
    )

    notify(
        category=Notification.Category.ACCIDENT,
        priority=Notification.Priority.HIGH if severity in (
            IncidentDetection.Severity.HIGH, IncidentDetection.Severity.CRITICAL
        ) else Notification.Priority.MEDIUM,
        title='Unusual congestion detected',
        message=(
            f'{intersection.name} is at {snapshot.vehicle_count} vehicles — about '
            f'{round(deviation * 100)}% above the usual level for this time. Worth a look.'
        ),
        intersection=intersection,
    )
    _broadcast_incident(incident)
    return incident


def _broadcast_forecast(intersection, predictions):
    payload = {
        'type': 'forecast.update',
        'intersection_id': str(intersection.pk),
        'intersection_name': intersection.name,
        'forecasts': [
            {
                'predicted_for': p.predicted_for.isoformat(),
                'predicted_level': p.predicted_level,
                'predicted_vehicle_count': p.predicted_vehicle_count,
                'confidence': p.confidence,
            }
            for p in predictions
        ],
        'generated_at': timezone.now().isoformat(),
    }
    _group_send(payload)


def _broadcast_incident(incident):
    payload = {
        'type': 'incident.alert',
        'incident_id': str(incident.pk),
        'intersection_id': str(incident.intersection_id),
        'intersection_name': incident.intersection.name,
        'incident_type': incident.incident_type,
        'severity': incident.severity,
        'confidence': incident.confidence,
        'detected_at': incident.detected_at.isoformat(),
    }
    _group_send(payload)


def _group_send(payload):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(PREDICTION_GROUP, {
        'type': payload['type'].replace('.', '_'),
        'payload': payload,
    })
