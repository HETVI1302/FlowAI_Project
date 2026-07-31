import json

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from monitoring.models import Intersection

from .models import Emission, TrafficStatistic

# Human labels for the CongestionLevel-style 1-4 score analytics/services.py
# writes into TrafficStatistic.avg_congestion_score, so the template can
# show "Moderate" instead of "2.3".
CONGESTION_SCORE_LABELS = {1: 'Low', 2: 'Moderate', 3: 'High', 4: 'Severe'}


def _congestion_label(score):
    return CONGESTION_SCORE_LABELS.get(round(score), 'Low') if score else 'Low'


@login_required(login_url='accounts:login')
def dashboard(request):
    """
    Analytics + Environmental Monitoring dashboard. Shows daily/weekly/
    monthly traffic rollups per intersection alongside city-wide emissions
    totals. Reads TrafficStatistic/Emission rows written by
    `run_analytics_rollup` rather than aggregating raw Vehicle rows here —
    keeps this page fast regardless of how much detection history has
    piled up.
    """
    period = request.GET.get('period', TrafficStatistic.Period.DAILY)
    if period not in TrafficStatistic.Period.values:
        period = TrafficStatistic.Period.DAILY
    intersections = list(Intersection.objects.order_by('name'))

    statistics = list(
        TrafficStatistic.objects.filter(period=period)
        .select_related('intersection')
        .order_by('-period_start', 'intersection__name')
    )

    # Most recent bucket per intersection
    latest_by_intersection = {}
    for stat in statistics:
        latest_by_intersection.setdefault(stat.intersection_id, stat)

    # Current local date/time boundaries
    today = timezone.localdate()
    tz = timezone.get_current_timezone()

    today_start = timezone.make_aware(
        timezone.datetime.combine(
            today,
            timezone.datetime.min.time()
        ),
        tz
    )

    tomorrow_start = today_start + timezone.timedelta(days=1)

    week_start_date = today - timezone.timedelta(
        days=today.weekday()
    )

    week_start = timezone.make_aware(
        timezone.datetime.combine(
            week_start_date,
            timezone.datetime.min.time()
        ),
        tz
    )

    # Today's emissions
    emissions_today = Emission.objects.filter(
        window_start__gte=today_start,
        window_start__lt=tomorrow_start
    ).aggregate(
        total_carbon=Sum('carbon_emission_kg'),
        total_fuel=Sum('fuel_consumption_liters')
    )

    # This week's emissions
    emissions_week = Emission.objects.filter(
        window_start__gte=week_start,
        window_start__lt=tomorrow_start
    ).aggregate(
        total_carbon=Sum('carbon_emission_kg'),
        total_fuel=Sum('fuel_consumption_liters')
    )

    # Intersection cards
    cards = [
        {
            'intersection': intersection,
            'statistic': latest_by_intersection.get(intersection.id),
            'congestion_label': _congestion_label(
                latest_by_intersection[
                    intersection.id
                ].avg_congestion_score
            ) if intersection.id in latest_by_intersection else None,
        }
        for intersection in intersections
    ]

    # Traffic-volume-by-intersection chart
    volume_chart_data = {
        'labels': [
            c['intersection'].name
            for c in cards
            if c['statistic']
        ],
        'vehicle_counts': [
            c['statistic'].total_vehicles
            for c in cards
            if c['statistic']
        ],
    }

    # Emissions trend - last 14 days
    emissions_history = (
        Emission.objects.filter(
            window_start__gte=(
                today_start - timezone.timedelta(days=13)
            ),
            window_start__lt=tomorrow_start
        )
        .extra(select={'day': "DATE(window_start)"})
        .values('day')
        .annotate(
            total_carbon=Sum('carbon_emission_kg')
        )
        .order_by('day')
    )

    emissions_chart_data = {
        'labels': [
            str(row['day'])
            for row in emissions_history
        ],
        'carbon_kg': [
            round(row['total_carbon'] or 0, 2)
            for row in emissions_history
        ],
    }
    return render(request, 'analytics/dashboard.html', {
        'period': period,
        'period_choices': TrafficStatistic.Period.choices,
        'cards': cards,
        'emissions_today': emissions_today,
        'emissions_week': emissions_week,
        'volume_chart_json': json.dumps(volume_chart_data),
        'emissions_chart_json': json.dumps(emissions_chart_data),
    })