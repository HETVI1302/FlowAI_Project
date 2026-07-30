import logging
import time

from django.core.management.base import BaseCommand

from monitoring.models import Intersection
from signals_app.optimizer import optimize_signal, revert_expired_emergencies

logger = logging.getLogger('signals_app.optimizer')

OPTIMIZE_INTERVAL_SECONDS = 15


class Command(BaseCommand):
    help = (
        'Runs the Signal Management optimizer loop as a standalone process: '
        'every OPTIMIZE_INTERVAL_SECONDS it re-evaluates every intersection '
        "whose signal is in DYNAMIC mode against that intersection's latest "
        'TrafficDensitySnapshot, and reverts any signal whose emergency-'
        'priority hold has expired. Run one instance city-wide (unlike the '
        'per-camera CV workers) — this is intended to be launched alongside '
        'them, e.g. as its own Docker service / supervisord process.'
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            f'Signal optimizer started (every {OPTIMIZE_INTERVAL_SECONDS}s)...'
        ))
        try:
            while True:
                revert_expired_emergencies()
                for intersection in Intersection.objects.filter(status=Intersection.Status.ACTIVE):
                    try:
                        optimize_signal(intersection)
                    except Exception:
                        logger.exception('Failed to optimize signal for %s', intersection)
                time.sleep(OPTIMIZE_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Signal optimizer stopped.'))
