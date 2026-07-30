import json

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.shortcuts import render
from django.utils import timezone

from analytics.models import Emission,TrafficStatistic
from monitoring.models import Intersection, TrafficDensitySnapshot, Vehicle
from notifications.models import Notification
from reports.models import Report
from signals_app.models import Signal

# Overall congestion level shown on the summary card is derived from the
# average vehicle_count across each intersection's latest snapshot, reusing
# the same thresholds the CV worker uses per-intersection (monitoring/cv/pipeline.py)
# so the city-wide label and the per-intersection badges never disagree.
CONGESTION_THRESHOLDS = (
    (5, TrafficDensitySnapshot.CongestionLevel.LOW),
    (15, TrafficDensitySnapshot.CongestionLevel.MODERATE),
    (30, TrafficDensitySnapshot.CongestionLevel.HIGH),
)


def _overall_congestion_level(avg_vehicle_count):
    for threshold, level in CONGESTION_THRESHOLDS:
        if avg_vehicle_count <= threshold:
            return level
    return TrafficDensitySnapshot.CongestionLevel.SEVERE


@login_required(login_url='accounts:login')
def home(request):
    """
    Live operations dashboard.
    Loads dashboard data from the database.
    """
    today = timezone.now().date()
    intersections = list(Intersection.objects.all())

    # Latest snapshot for every intersection
    latest_snapshots = [
        snap
        for snap in (
            TrafficDensitySnapshot.objects
            .filter(intersection=i)
            .order_by('-captured_at')
            .first()
            for i in intersections
        )
        if snap is not None
    ]

    # Latest analytics records
    latest_traffic = TrafficStatistic.objects.order_by('-created_at').first()
    latest_emission = Emission.objects.order_by('-created_at').first()

    # Vehicles
    total_vehicles_today = (
        latest_traffic.total_vehicles
        if latest_traffic
        else 0
    )

    # Average vehicle count from latest snapshots
    avg_vehicle_count = (
        sum(s.vehicle_count for s in latest_snapshots)
        / len(latest_snapshots)
        if latest_snapshots
        else 0
    )

    # Average waiting time
    avg_waiting_time = (
        latest_traffic.avg_waiting_time_seconds
        if latest_traffic
        else 0
    )

    # Latest emission information
    emissions_today = {
        'total_carbon': (
            latest_emission.carbon_emission_kg
            if latest_emission
            else 0
        ),
        'total_fuel': (
            latest_emission.fuel_consumption_liters
            if latest_emission
            else 0
        ),
    }

    # Signals
    signals = list(
        Signal.objects
        .select_related('intersection')
        .order_by('intersection__name')
    )

    signal_mode_counts = (
        Signal.objects
        .values('mode')
        .annotate(count=Count('id'))
    )

    # Notifications
    notifications = list(
        Notification.objects.order_by('-created_at')[:8]
    )

    unread_notification_count = (
        Notification.objects.filter(is_read=False).count()
    )

    # Reports
    recent_reports = list(
        Report.objects.order_by('-created_at')[:5]
    )

    # Last 20 traffic snapshots for trend chart
    trend_snapshots = list(
        TrafficDensitySnapshot.objects
        .order_by('-captured_at')[:20]
    )[::-1]

    trend_chart_data = {
        'labels': [
            s.captured_at.strftime('%H:%M')
            for s in trend_snapshots
        ],
        'vehicle_counts': [
            s.vehicle_count
            for s in trend_snapshots
        ],
    }
    
    print("TREND CHART DATA =", trend_chart_data)

    # Congestion chart
    congestion_chart_data = {
        'labels': [
            s.intersection.name
            for s in latest_snapshots
        ],
        'vehicle_counts': [
            s.vehicle_count
            for s in latest_snapshots
        ],
        'levels': [
            s.congestion_level
            for s in latest_snapshots
        ],
    }

    # Dashboard context
    context = {
        'active_intersections_count': sum(
            1
            for i in intersections
            if i.status == Intersection.Status.ACTIVE
        ),
        'total_intersections_count': len(intersections),
        'total_vehicles_today': total_vehicles_today,
        'avg_waiting_time': round(avg_waiting_time, 1),
        'overall_congestion_level': _overall_congestion_level(
            avg_vehicle_count
        ),
        'emissions_today': emissions_today,
        'signals': signals,
        'signal_mode_counts': signal_mode_counts,
        'notifications': notifications,
        'unread_notification_count': unread_notification_count,
        'recent_reports': recent_reports,
        'trend_chart_json': trend_chart_data,
        'congestion_chart_json': congestion_chart_data,
    }

    return render(
        request,
        'dashboard/home.html',
        context
    )