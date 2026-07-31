"""
Analytics + Environmental Monitoring module. Two responsibilities, meant to
be run periodically per-intersection (see run_analytics_rollup):

  * build_traffic_statistics(intersection, period) — rolls up raw Vehicle /
    TrafficDensitySnapshot rows into a single TrafficStatistic row for the
    given period bucket (today for DAILY, the Monday of this week for
    WEEKLY, the 1st of this month for MONTHLY). Uses update_or_create keyed
    on the model's unique_together, so re-running mid-period recomputes
    that bucket in place rather than duplicating it — safe to call on
    every rollup tick.

  * estimate_emissions(intersection, window_start, window_end) — turns the
    Vehicle detections in a time window into a rough environmental-impact
    estimate (fuel burned, CO2, a composite pollution index) using
    per-vehicle-type emission factors. This is a back-of-envelope model,
    not a calibrated one — good enough to drive the Environmental
    Monitoring cards/charts for a demo, not for regulatory reporting.

Both are read by analytics/views.py to render the Chart.js dashboards, and
by reports/services.py when a report snapshot needs numbers to export.
"""
import logging
from datetime import datetime, time, timedelta

from django.db.models import Avg, Count
from django.utils import timezone

from monitoring.models import TrafficDensitySnapshot, Vehicle

from .models import Emission, TrafficStatistic

logger = logging.getLogger('analytics.engine')

# Rough grams-of-CO2-per-km and liters-of-fuel-per-km by vehicle type.
# Motorcycles are cleanest, buses/trucks worst per-vehicle (even though
# they move more people/goods per vehicle — this module counts vehicles,
# not passenger-km, since that's what the CV pipeline actually detects).
EMISSION_FACTORS = {
    Vehicle.VehicleType.CAR: {'co2_g_per_km': 180, 'fuel_l_per_km': 0.08},
    Vehicle.VehicleType.MOTORCYCLE: {'co2_g_per_km': 90, 'fuel_l_per_km': 0.03},
    Vehicle.VehicleType.BUS: {'co2_g_per_km': 900, 'fuel_l_per_km': 0.35},
    Vehicle.VehicleType.TRUCK: {'co2_g_per_km': 950, 'fuel_l_per_km': 0.38},
    Vehicle.VehicleType.AMBULANCE: {'co2_g_per_km': 220, 'fuel_l_per_km': 0.10},
    Vehicle.VehicleType.POLICE: {'co2_g_per_km': 180, 'fuel_l_per_km': 0.08},
    Vehicle.VehicleType.OTHER: {'co2_g_per_km': 180, 'fuel_l_per_km': 0.08},
}
# A vehicle idling in a queue burns fuel without covering distance — modeled
# separately as a flat rate per second of estimated wait, added on top of
# the per-vehicle pass-through factors above.
IDLE_FUEL_L_PER_SECOND = 0.0006
IDLE_CO2_G_PER_SECOND = 1.4
# Distance assumed "covered" by a vehicle passing through the intersection
# window, for the per-km factors above — deliberately small since this
# models the intersection approach, not a full trip.
ASSUMED_PASS_THROUGH_KM = 0.15


def _period_bounds(period):
    """Returns (period_start_date, window_start_dt, window_end_dt) for the
    bucket that "now" currently falls in, for the given TrafficStatistic
    period choice."""
    now = timezone.localtime()
    today = now.date()

    if period == TrafficStatistic.Period.DAILY:
        period_start = today
    elif period == TrafficStatistic.Period.WEEKLY:
        period_start = today - timedelta(days=today.weekday())  # Monday
    elif period == TrafficStatistic.Period.MONTHLY:
        period_start = today.replace(day=1)
    else:
        raise ValueError(f'Unknown period: {period}')

    window_start = timezone.make_aware(datetime.combine(period_start, time.min))
    window_end = now
    return period_start, window_start, window_end


def build_traffic_statistics(intersection, period):
    """Recomputes the TrafficStatistic row for the current bucket of the
    given period, from raw Vehicle counts and TrafficDensitySnapshot
    averages. Returns the (possibly newly created) TrafficStatistic."""
    period_start, window_start, window_end = _period_bounds(period)

    vehicle_qs = Vehicle.objects.filter(
        intersection=intersection, timestamp__gte=window_start, timestamp__lte=window_end
    )
    total_vehicles = vehicle_qs.count()

    snapshot_qs = TrafficDensitySnapshot.objects.filter(
        intersection=intersection, captured_at__gte=window_start, captured_at__lte=window_end
    )
    snapshot_aggregates = snapshot_qs.aggregate(
        avg_waiting=Avg('avg_waiting_time_seconds')
    )
    avg_waiting_time = snapshot_aggregates['avg_waiting'] or 0

    # Congestion score reuses the same 1-4 scale prediction/services.py
    # uses, so analytics and prediction never disagree about what
    # "moderate" means numerically.
    congestion_score_map = {
        TrafficDensitySnapshot.CongestionLevel.LOW: 1,
        TrafficDensitySnapshot.CongestionLevel.MODERATE: 2,
        TrafficDensitySnapshot.CongestionLevel.HIGH: 3,
        TrafficDensitySnapshot.CongestionLevel.SEVERE: 4,
    }
    scored_snapshots = [congestion_score_map[s] for s in snapshot_qs.values_list('congestion_level', flat=True)]
    avg_congestion_score = sum(scored_snapshots) / len(scored_snapshots) if scored_snapshots else 0

    # Peak hour: the hour-of-day with the most vehicle detections so far
    # in this bucket. Cheap enough to compute from the vehicle_qs directly
    # rather than needing a separate hourly rollup table.
    hourly_counts = {}
    for ts in vehicle_qs.values_list('timestamp', flat=True):
        local_hour = timezone.localtime(ts).hour
        hourly_counts[local_hour] = hourly_counts.get(local_hour, 0) + 1
    peak_hour = max(hourly_counts, key=hourly_counts.get) if hourly_counts else None

    statistic, _created = TrafficStatistic.objects.update_or_create(
        intersection=intersection, period=period, period_start=period_start,
        defaults={
            'total_vehicles': total_vehicles,
            'avg_congestion_score': round(avg_congestion_score, 2),
            'avg_waiting_time_seconds': round(avg_waiting_time, 1),
            'peak_hour': peak_hour,
        },
    )
    return statistic


def estimate_emissions(intersection, window_start, window_end):
    """Aggregates Vehicle detections in [window_start, window_end) into one
    Emission row for the intersection. Skips creating a row if no vehicles
    were detected in the window (nothing to estimate)."""
    vehicle_counts = (
        Vehicle.objects.filter(intersection=intersection, timestamp__gte=window_start, timestamp__lt=window_end)
        .values('vehicle_type').annotate(count=Count('id'))
    )
    if not vehicle_counts:
        return None

    total_fuel = 0.0
    total_co2_g = 0.0
    total_vehicles = 0
    for row in vehicle_counts:
        factors = EMISSION_FACTORS.get(row['vehicle_type'], EMISSION_FACTORS[Vehicle.VehicleType.OTHER])
        count = row['count']
        total_vehicles += count
        total_fuel += count * factors['fuel_l_per_km'] * ASSUMED_PASS_THROUGH_KM
        total_co2_g += count * factors['co2_g_per_km'] * ASSUMED_PASS_THROUGH_KM

    # Idle contribution, using the window's average waiting time as a proxy
    # for how long each vehicle sat idling in the queue.
    avg_waiting = (
        TrafficDensitySnapshot.objects.filter(
            intersection=intersection, captured_at__gte=window_start, captured_at__lt=window_end
        ).aggregate(avg=Avg('avg_waiting_time_seconds'))['avg'] or 0
    )
    idle_seconds_total = avg_waiting * total_vehicles
    total_fuel += idle_seconds_total * IDLE_FUEL_L_PER_SECOND
    total_co2_g += idle_seconds_total * IDLE_CO2_G_PER_SECOND

    # Pollution index: a unitless composite (0-100+) combining CO2 density
    # and idle time, purely for the dashboard gauge — not a calibrated AQI.
    pollution_index = min(100.0, (total_co2_g / max(total_vehicles, 1)) / 5 + (avg_waiting / 10))

    emission = Emission.objects.create(
        intersection=intersection,
        carbon_emission_kg=round(total_co2_g / 1000, 3),
        fuel_consumption_liters=round(total_fuel, 3),
        pollution_index=round(pollution_index, 1),
        idle_time_seconds=round(idle_seconds_total, 1),
        window_start=window_start,
        window_end=window_end,
    )
    return emission


def run_rollup_for_intersection(intersection, emission_window_minutes=60):
    """Convenience wrapper used by the management command: refreshes all
    three TrafficStatistic periods and writes one Emission row for the
    trailing `emission_window_minutes`."""
    for period in TrafficStatistic.Period.values:
        build_traffic_statistics(intersection, period)

    now = timezone.now()
    estimate_emissions(intersection, now - timedelta(minutes=emission_window_minutes), now)
