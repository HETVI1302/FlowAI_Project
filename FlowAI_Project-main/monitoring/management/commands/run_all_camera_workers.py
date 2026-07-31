import subprocess
import sys

from django.core.management.base import BaseCommand

from monitoring.models import Camera


class Command(BaseCommand):
    help = (
        'Dev/demo convenience: spawns one `run_camera_worker` subprocess per '
        'camera whose intersection status is ACTIVE. For production, run '
        '`run_camera_worker <id>` under a real process manager (Docker '
        'Compose service replicas, systemd units, or Kubernetes pods) '
        'instead, so a crashed camera worker is restarted independently.'
    )

    def handle(self, *args, **options):
        cameras = Camera.objects.filter(intersection__status='active')
        if not cameras.exists():
            self.stdout.write(self.style.WARNING('No active cameras found — nothing to launch.'))
            return

        processes = []
        for camera in cameras:
            self.stdout.write(f'Launching worker for {camera.name or camera.id} ({camera.intersection.name})...')
            processes.append(subprocess.Popen(
                [sys.executable, 'manage.py', 'run_camera_worker', str(camera.id)]
            ))

        self.stdout.write(self.style.SUCCESS(f'{len(processes)} camera worker(s) running. Ctrl+C to stop all.'))
        try:
            for process in processes:
                process.wait()
        except KeyboardInterrupt:
            self.stdout.write('Stopping all camera workers...')
            for process in processes:
                process.terminate()
