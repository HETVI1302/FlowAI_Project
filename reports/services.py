"""
Report generation. `generate_report(report)` fills in an existing pending
Report row (created by the view) with an actual file, synchronously — for
the scale of a single hackathon deployment this is fast enough (a handful
of DB rows -> a file) to run in the request/response cycle rather than
needing a Celery-style task queue. If report volume grows, swap the call
site in reports/views.py for a background task without touching this
function's contract: it always takes a Report row and leaves it either
READY (with `.file` populated) or FAILED.

Data source: TrafficStatistic + Emission rows already written by
analytics/services.py — reports summarize what analytics has already
computed rather than re-aggregating raw Vehicle rows themselves.
"""
import csv
import io
import logging

from django.core.files.base import ContentFile
from django.utils import timezone

from analytics.models import Emission, TrafficStatistic

logger = logging.getLogger('reports.engine')


def _collect_rows(report):
    """Returns (traffic_stats, emissions) querysets scoped to the report's
    intersection (or all intersections, for a city-wide report) and date range."""
    stats = TrafficStatistic.objects.filter(
        period_start__gte=report.period_start, period_start__lte=report.period_end
    ).select_related('intersection')
    emissions = Emission.objects.filter(
        window_start__date__gte=report.period_start, window_start__date__lte=report.period_end
    ).select_related('intersection')

    if report.intersection_id:
        stats = stats.filter(intersection_id=report.intersection_id)
        emissions = emissions.filter(intersection_id=report.intersection_id)

    return list(stats.order_by('intersection__name', 'period_start')), list(emissions.order_by('intersection__name', 'window_start'))


def _build_csv(stats, emissions):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['-- Traffic Statistics --'])
    writer.writerow(['Intersection', 'Period', 'Period Start', 'Total Vehicles', 'Avg Congestion Score', 'Avg Waiting Time (s)', 'Peak Hour'])
    for s in stats:
        writer.writerow([s.intersection.name, s.period, s.period_start, s.total_vehicles, s.avg_congestion_score, s.avg_waiting_time_seconds, s.peak_hour])

    writer.writerow([])
    writer.writerow(['-- Emissions --'])
    writer.writerow(['Intersection', 'Window Start', 'Window End', 'Carbon (kg)', 'Fuel (L)', 'Pollution Index'])
    for e in emissions:
        writer.writerow([e.intersection.name, e.window_start, e.window_end, e.carbon_emission_kg, e.fuel_consumption_liters, e.pollution_index])

    return buffer.getvalue().encode('utf-8')


def _build_xlsx(stats, emissions):
    from openpyxl import Workbook

    workbook = Workbook()
    stats_sheet = workbook.active
    stats_sheet.title = 'Traffic Statistics'
    stats_sheet.append(['Intersection', 'Period', 'Period Start', 'Total Vehicles', 'Avg Congestion Score', 'Avg Waiting Time (s)', 'Peak Hour'])
    for s in stats:
        stats_sheet.append([s.intersection.name, s.period, str(s.period_start), s.total_vehicles, s.avg_congestion_score, s.avg_waiting_time_seconds, s.peak_hour])

    emissions_sheet = workbook.create_sheet('Emissions')
    emissions_sheet.append(['Intersection', 'Window Start', 'Window End', 'Carbon (kg)', 'Fuel (L)', 'Pollution Index'])
    for e in emissions:
        emissions_sheet.append([e.intersection.name, str(e.window_start), str(e.window_end), e.carbon_emission_kg, e.fuel_consumption_liters, e.pollution_index])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _build_pdf(report, stats, emissions):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f'FlowAI — {report.get_report_type_display()}', styles['Title']),
        Paragraph(
            f'{report.intersection.name if report.intersection else "City-wide"} · '
            f'{report.period_start} to {report.period_end}',
            styles['Normal'],
        ),
        Spacer(1, 16),
        Paragraph('Traffic Statistics', styles['Heading2']),
    ]

    stats_data = [['Intersection', 'Period', 'Start', 'Vehicles', 'Congestion', 'Avg Wait (s)', 'Peak Hr']]
    for s in stats:
        stats_data.append([s.intersection.name, s.period, str(s.period_start), s.total_vehicles, s.avg_congestion_score, s.avg_waiting_time_seconds, s.peak_hour])
    elements.append(_styled_table(stats_data))

    elements.append(Spacer(1, 16))
    elements.append(Paragraph('Environmental Impact', styles['Heading2']))
    emissions_data = [['Intersection', 'Window Start', 'CO2 (kg)', 'Fuel (L)', 'Pollution Idx']]
    for e in emissions:
        emissions_data.append([e.intersection.name, str(e.window_start), e.carbon_emission_kg, e.fuel_consumption_liters, e.pollution_index])
    elements.append(_styled_table(emissions_data))

    doc.build(elements)
    return buffer.getvalue()


def _styled_table(data):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1b2440')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f4f6fb')]),
    ]))
    return table


BUILDERS = {
    'csv': lambda report, stats, emissions: (_build_csv(stats, emissions), 'text/csv', 'csv'),
    'xlsx': lambda report, stats, emissions: (_build_xlsx(stats, emissions), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'xlsx'),
    'pdf': lambda report, stats, emissions: (_build_pdf(report, stats, emissions), 'application/pdf', 'pdf'),
}


def generate_report(report):
    """Fills in `report.file` and flips status to READY (or FAILED on
    error). Returns the report."""
    report.status = report.Status.GENERATING
    report.save(update_fields=['status'])

    try:
        stats, emissions = _collect_rows(report)
        builder = BUILDERS[report.file_format]
        content_bytes, _mime, extension = builder(report, stats, emissions)

        filename = f'flowai_{report.report_type}_{report.period_start}_{report.period_end}.{extension}'
        report.file.save(filename, ContentFile(content_bytes), save=False)
        report.status = report.Status.READY
        report.completed_at = timezone.now()
        report.save(update_fields=['file', 'status', 'completed_at'])
    except Exception:
        logger.exception('Report generation failed for report %s', report.pk)
        report.status = report.Status.FAILED
        report.save(update_fields=['status'])

    return report
