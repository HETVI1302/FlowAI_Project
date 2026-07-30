import logging
import time

from django.core.management.base import BaseCommand

from monitoring.models import Intersection
from prediction.services import build_traffic_patterns, detect_anomalies, generate_forecasts

logger = logging.getLogger('prediction.engine')

ENGINE_INTERVAL_SECONDS = 60


class Command(BaseCommand):
    help = (
        'Runs the AI Prediction engine as a standalone process: every '
        'ENGINE_INTERVAL_SECONDS it rolls new TrafficDensitySnapshots into '
        "each active intersection's TrafficPattern baseline, regenerates its "
        'congestion forecasts, and checks the latest snapshot for anomalies. '
        'Run one instance city-wide, alongside the CV workers and signal '
        'optimizer (see run_camera_worker / run_signal_optimizer).'
    )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            f'Prediction engine started (every {ENGINE_INTERVAL_SECONDS}s)...'
        ))
        try:
            while True:
                for intersection in Intersection.objects.filter(status=Intersection.Status.ACTIVE):
                    try:
                        build_traffic_patterns(intersection)
                        generate_forecasts(intersection)
                        detect_anomalies(intersection)
                    except Exception:
                        logger.exception('Prediction pass failed for %s', intersection)
                time.sleep(ENGINE_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Prediction engine stopped.'))
