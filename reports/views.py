from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# @login_required
def reports_dashboard(request):
    """
    Renders the reporting and analytics dashboard.
    In a real app, we would fetch data from analytics/monitoring models here.
    """
    return render(request, 'reports/index.html')
