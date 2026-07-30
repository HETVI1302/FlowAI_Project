from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required(login_url='accounts:login')
def center(request):
    """
    Full notification history. The unread badge in the nav (static/js/
    notifications.js) updates live over ws/notifications/ as new alerts
    come in; this page itself renders from the DB so history survives
    past whatever the socket has seen since the tab opened.
    """
    notifications = Notification.objects.order_by('-created_at')[:100]
    return render(request, 'notifications/center.html', {
        'notifications': notifications,
        'unread_count': Notification.objects.filter(is_read=False).count(),
    })


@login_required(login_url='accounts:login')
def unread_count(request):
    """Polled once on page load by every page (not just the center) so the
    nav badge is correct before the WebSocket has had a chance to push
    anything new."""
    return JsonResponse({'unread_count': Notification.objects.filter(is_read=False).count()})


@login_required(login_url='accounts:login')
@require_POST
def mark_read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'unread_count': Notification.objects.filter(is_read=False).count()})
    return redirect('notifications:center')


@login_required(login_url='accounts:login')
@require_POST
def mark_all_read(request):
    Notification.objects.filter(is_read=False).update(is_read=True)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'unread_count': 0})
    return redirect('notifications:center')
