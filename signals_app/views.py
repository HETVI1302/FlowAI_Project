from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import User

from .models import Signal, SignalChangeLog

OPERATOR_ROLES = {User.Role.ADMIN, User.Role.OPERATOR}


@login_required(login_url='accounts:login')
def control_panel(request):
    """
    Signal Management dashboard — one glass card per intersection's signal,
    live-updated over ws/signals/overview/ (static/js/signals.js) whenever
    the AI optimizer retimes it or an emergency-priority override fires.
    Manual override controls only render for operator+ roles; viewers/
    analysts get a read-only view of the same live data.
    """
    signals = list(
        Signal.objects.select_related('intersection').order_by('intersection__name')
    )
    recent_changes = list(
        SignalChangeLog.objects.select_related('signal__intersection').order_by('-changed_at')[:15]
    )
    return render(request, 'signals_app/control.html', {
        'signals': signals,
        'recent_changes': recent_changes,
        'can_override': request.user.role in OPERATOR_ROLES,
        'modes': Signal.Mode.choices,
    })


@login_required(login_url='accounts:login')
@require_POST
def manual_override(request, signal_id):
    """
    Operator sets a fixed timing and flips the signal to MANUAL mode,
    taking it out of the AI optimizer's hands until switched back to
    DYNAMIC. Rejected for viewer/analyst roles — this changes real
    intersection behavior, not just a display setting.
    """
    if request.user.role not in OPERATOR_ROLES:
        messages.error(request, "You don't have permission to change signal timing.")
        return redirect('signals_app:control_panel')

    signal = get_object_or_404(Signal, pk=signal_id)
    try:
        green_time = int(request.POST.get('green_time', signal.green_time))
        yellow_time = int(request.POST.get('yellow_time', signal.yellow_time))
    except (TypeError, ValueError):
        messages.error(request, 'Timing values must be whole numbers of seconds.')
        return redirect('signals_app:control_panel')

    if not (5 <= green_time <= 120) or not (2 <= yellow_time <= 10):
        messages.error(request, 'Green time must be 5-120s and yellow time 2-10s.')
        return redirect('signals_app:control_panel')

    previous_green = signal.green_time
    signal.green_time = green_time
    signal.yellow_time = yellow_time
    signal.red_time = green_time + yellow_time
    signal.mode = Signal.Mode.MANUAL
    signal.last_updated_by = request.user.get_full_name() or request.user.username
    signal.save(update_fields=['green_time', 'yellow_time', 'red_time', 'mode', 'last_updated_by', 'updated_at'])

    SignalChangeLog.objects.create(
        signal=signal,
        previous_green_time=previous_green,
        new_green_time=green_time,
        reason='Manual override by operator',
        triggered_by=signal.last_updated_by,
    )
    # Import kept local to avoid a hard import cycle at module load — optimizer
    # imports notifications, not signals_app, so this is safe, but keeping the
    # broadcast helper import next to its one use here is clearer.
    from .optimizer import _broadcast_signal_update
    _broadcast_signal_update(signal, reason='manual_override')

    messages.success(request, f'{signal.intersection.name} signal updated to {green_time}s green.')
    return redirect('signals_app:control_panel')


@login_required(login_url='accounts:login')
@require_POST
def set_dynamic_mode(request, signal_id):
    """Hands a signal back to the AI optimizer."""
    if request.user.role not in OPERATOR_ROLES:
        messages.error(request, "You don't have permission to change signal mode.")
        return redirect('signals_app:control_panel')

    signal = get_object_or_404(Signal, pk=signal_id)
    signal.mode = Signal.Mode.DYNAMIC
    signal.last_updated_by = request.user.get_full_name() or request.user.username
    signal.save(update_fields=['mode', 'last_updated_by', 'updated_at'])

    SignalChangeLog.objects.create(
        signal=signal,
        previous_green_time=signal.green_time,
        new_green_time=signal.green_time,
        reason='Returned to AI-optimized mode by operator',
        triggered_by=signal.last_updated_by,
    )
    from .optimizer import _broadcast_signal_update
    _broadcast_signal_update(signal, reason='returned_to_dynamic')

    messages.success(request, f'{signal.intersection.name} signal returned to AI optimization.')
    return redirect('signals_app:control_panel')
