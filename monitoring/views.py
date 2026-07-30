from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Camera, Intersection, TrafficDensitySnapshot


@login_required(login_url='accounts:login')
def live_monitoring(request):
    """
    Camera grid — one glass card per camera, each hooked up client-side to
    ws/monitoring/overview/ for live vehicle counts and congestion badges.
    Initial render uses the latest persisted snapshot per intersection so
    the page isn't empty for the few seconds before the socket connects.
    """
    intersections = list(Intersection.objects.prefetch_related('cameras').order_by('name'))
    # `.distinct(field)` (DISTINCT ON) is Postgres-only, and this project runs
    # MySQL — so the latest-per-intersection snapshot is fetched with one
    # query per intersection instead. Fine at hackathon/demo scale; if the
    # intersection count grows, replace with a MySQL 8 window-function query.
    #
    # Built as a flat list of cards (rather than a dict keyed by id) because
    # Django templates can't do `dict[variable_key]` lookups — this way the
    # template just loops and uses dot access, no custom filter needed.
    cards = []
    for intersection in intersections:
        snapshot = (
            TrafficDensitySnapshot.objects.filter(intersection=intersection)
            .order_by('-captured_at').first()
        )
        cards.append({
            'intersection': intersection,
            'camera_count': intersection.cameras.count(),
            'snapshot': snapshot,
        })
    return render(request, 'monitoring/live.html', {'cards': cards})


@login_required(login_url='accounts:login')
def intersection_detail(request, intersection_id):
    """Single-intersection deep dive, subscribed to ws/monitoring/<id>/."""
    intersection = get_object_or_404(Intersection.objects.prefetch_related('cameras'), pk=intersection_id)
    latest_snapshot = TrafficDensitySnapshot.objects.filter(intersection=intersection).order_by('-captured_at').first()
    return render(request, 'monitoring/detail.html', {
        'intersection': intersection,
        'latest_snapshot': latest_snapshot,
    })
