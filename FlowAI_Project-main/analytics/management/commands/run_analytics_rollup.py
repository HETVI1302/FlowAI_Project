"""
Background worker that periodically recomputes TrafficStatistic rollups and
writes a fresh Emission estimate for every intersection. Run alongside the
camera workers, signal optimizer, and prediction engine:

    python manage.py run_analytics_rollup

Deliberately coarse-grained (default every 5 minutes) — unlike the CV
pipeline or signal optimizer, analytics rollups don't need to react in
real time, they just need to stay reasonably fresh for the dashboards.
"""
import logging
import time

from django.core.management.base import BaseCommand

from analytics.services import run_rollup_for_intersection
from monitoring.models import Intersection

logger = logging.getLogger('analytics.engine')


class Command(BaseCommand):
    help = 'Periodically rolls up traffic statistics and emissions estimates for all intersections.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval', type=int, default=300,
            help='Seconds between rollup passes (default: 300 = 5 minutes).'
        )
        parser.add_argument(
            '--once', action='store_true',
            help='Run a single pass and exit, instead of looping forever.'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']

        self.stdout.write(self.style.SUCCESS(
            f'Starting analytics rollup worker (interval={interval}s, once={run_once})'
        ))

        while True:
            intersections = list(Intersection.objects.all())
            for intersection in intersections:
                try:
                    run_rollup_for_intersection(intersection)
                except Exception:
                    logger.exception('Rollup failed for intersection %s', intersection.pk)

            self.stdout.write(f'Rolled up {len(intersections)} intersection(s).')

            if run_once:
                break
            time.sleep(interval)
