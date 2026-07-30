from django.core.management.base import BaseCommand, CommandError

from monitoring.cv.pipeline import CameraWorker
from monitoring.models import Camera


class Command(BaseCommand):
    help = (
        'Runs the YOLOv8/OpenCV detection loop for a single camera as a '
        'standalone process. Intended to be run one-per-camera (e.g. under '
        'systemd, supervisord, or a Docker service replica) rather than '
        'inside the Django web process. See run_all_camera_workers for a '
        'dev-only convenience wrapper that spawns one per active camera.'
    )

    def add_arguments(self, parser):
        parser.add_argument('camera_id', type=str, help='UUID of the Camera to process')

    def handle(self, *args, **options):
        camera_id = options['camera_id']
        if not Camera.objects.filter(pk=camera_id).exists():
            raise CommandError(f'No camera found with id={camera_id}')

        self.stdout.write(self.style.SUCCESS(f'Starting camera worker for {camera_id}...'))
        worker = CameraWorker(camera_id)
        worker.run()
