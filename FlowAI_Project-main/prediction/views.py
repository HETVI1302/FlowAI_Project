from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from monitoring.models import Intersection

from .models import CongestionPrediction, IncidentDetection


@login_required(login_url='accounts:login')
def forecast(request):
    """
    AI Prediction dashboard: latest forecast horizons per intersection
    (live-updated over ws/prediction/overview/, see static/js/prediction.js)
    plus the open/recent incident list. Initial render pulls the most
    recently generated CongestionPrediction per (intersection, horizon) so
    the page isn't empty before the engine's next tick.
    """
    intersections = list(Intersection.objects.order_by('name'))

    cards = []
    for intersection in intersections:
        # Latest batch of forecasts sharing the same generated_at rather than
        # one query per horizon — the engine writes all horizons for an
        # intersection together, so grouping by the newest few rows is enough.
        recent_predictions = list(
            CongestionPrediction.objects.filter(intersection=intersection).order_by('-predicted_for')[:3]
        )
        cards.append({
            'intersection': intersection,
            'predictions': recent_predictions,
        })

    open_incidents = list(
        IncidentDetection.objects.filter(is_resolved=False).select_related('intersection').order_by('-detected_at')
    )
    resolved_incidents = list(
        IncidentDetection.objects.filter(is_resolved=True).select_related('intersection').order_by('-resolved_at')[:10]
    )

    return render(request, 'prediction/forecast.html', {
        'cards': cards,
        'open_incidents': open_incidents,
        'resolved_incidents': resolved_incidents,
    })


@login_required(login_url='accounts:login')
@require_POST
def resolve_incident(request, incident_id):
    incident = get_object_or_404(IncidentDetection, pk=incident_id)
    incident.is_resolved = True
    incident.resolved_at = timezone.now()
    incident.save(update_fields=['is_resolved', 'resolved_at'])
    messages.success(request, f'Incident at {incident.intersection.name} marked resolved.')
    return redirect('prediction:forecast')
