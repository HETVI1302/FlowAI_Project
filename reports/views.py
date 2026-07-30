from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from monitoring.models import Intersection

from .models import Report
from .services import generate_report


@login_required(login_url='accounts:login')
def report_list(request):
    """Analytics report library: request a new daily/weekly/monthly/custom
    export and download previously generated ones. Generation runs
    synchronously (see reports/services.py) so a report is either READY or
    FAILED by the time this page reloads after a request."""
    reports = list(Report.objects.select_related('intersection', 'generated_by').order_by('-created_at')[:50])
    intersections = list(Intersection.objects.order_by('name'))

    return render(request, 'reports/list.html', {
        'reports': reports,
        'intersections': intersections,
        'report_types': Report.ReportType.choices,
        'formats': Report.Format.choices,
    })


@login_required(login_url='accounts:login')
@require_POST
def request_report(request):
    intersection_id = request.POST.get('intersection_id') or None
    intersection = get_object_or_404(Intersection, pk=intersection_id) if intersection_id else None

    report = Report.objects.create(
        intersection=intersection,
        generated_by=request.user,
        report_type=request.POST.get('report_type', Report.ReportType.DAILY),
        file_format=request.POST.get('file_format', Report.Format.PDF),
        period_start=request.POST['period_start'],
        period_end=request.POST['period_end'],
    )
    generate_report(report)

    if report.status == Report.Status.READY:
        messages.success(request, f'{report.get_report_type_display()} generated.')
    else:
        messages.error(request, 'Report generation failed — check the server logs.')

    return redirect('reports:list')


@login_required(login_url='accounts:login')
def download_report(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    if report.status != Report.Status.READY or not report.file:
        raise Http404('Report is not ready.')
    return FileResponse(report.file.open('rb'), as_attachment=True, filename=report.file.name.split('/')[-1])
