"""
Runs as its own OS process (one per active camera, launched by the
`run_camera_worker` management command) — this is the "background worker
/ separate microservice" called for in the architecture requirement.
It never runs on the Django HTTP thread.

Loop per frame:
  1. Grab a frame via OpenCV.
  2. Every `DETECTION_INTERVAL_SECONDS`, run YOLOv8 on it.
  3. Persist a Vehicle row per detection.
  4. Every `SNAPSHOT_INTERVAL_SECONDS`, roll the recent detections up into a
     TrafficDensitySnapshot (queue length / waiting time / congestion level)
     and push both an update and (if warranted) an emergency alert onto the
     Channels group so connected dashboards update live.
"""
import logging
import time
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from monitoring.consumers import OVERVIEW_GROUP, intersection_group_name
from monitoring.models import Camera, TrafficDensitySnapshot, Vehicle

from .detector import VehicleDetector

logger = logging.getLogger('monitoring.cv')

DETECTION_INTERVAL_SECONDS = 1.0
SNAPSHOT_INTERVAL_SECONDS = 60

# Rough heuristic: every queued vehicle adds this many seconds of estimated
# wait, capped by congestion thresholds below. A fine-tuned queueing model
# can replace `_estimate_waiting_time` without touching the rest of the loop.
SECONDS_PER_QUEUED_VEHICLE = 2.5
CONGESTION_THRESHOLDS = {  # vehicle_count -> level, checked in ascending order
    5: TrafficDensitySnapshot.CongestionLevel.LOW,
    15: TrafficDensitySnapshot.CongestionLevel.MODERATE,
    30: TrafficDensitySnapshot.CongestionLevel.HIGH,
}


def _congestion_level(vehicle_count):
    for threshold, level in CONGESTION_THRESHOLDS.items():
        if vehicle_count <= threshold:
            return level
    return TrafficDensitySnapshot.CongestionLevel.SEVERE


def _estimate_waiting_time(vehicle_count):
    return round(vehicle_count * SECONDS_PER_QUEUED_VEHICLE, 1)


class CameraWorker:
    def __init__(self, camera_id):
        self.camera_id = camera_id
        self.channel_layer = get_channel_layer()
        self._recent_detections = []
        self._last_snapshot_at = time.monotonic()

    def run(self):
        camera = Camera.objects.select_related('intersection').get(pk=self.camera_id)
        detector = VehicleDetector()
        capture = self._open_capture(camera.camera_url)

        self._set_camera_status(camera, Camera.Status.ONLINE)
        logger.info('Camera worker started for %s (%s)', camera.name, camera.camera_url)

        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    logger.warning('Camera %s dropped a frame / stream ended, retrying...', camera.name)
                    self._set_camera_status(camera, Camera.Status.ERROR)
                    time.sleep(2)
                    capture = self._open_capture(camera.camera_url)
                    self._set_camera_status(camera, Camera.Status.ONLINE)
                    continue

                detections = detector.detect(frame)
                self._persist_vehicles(camera, detections)
                self._recent_detections.extend(detections)
                self._heartbeat(camera)

                if time.monotonic() - self._last_snapshot_at >= SNAPSHOT_INTERVAL_SECONDS:
                    self._flush_snapshot(camera)

                time.sleep(DETECTION_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info('Camera worker for %s stopped.', camera.name)
        finally:
            capture.release()
            self._set_camera_status(camera, Camera.Status.OFFLINE)

    @staticmethod
    def _open_capture(camera_url):
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError(
                'opencv-python-headless is not installed. Run '
                '`pip install opencv-python-headless --break-system-packages`.'
            ) from exc
        return cv2.VideoCapture(camera_url)

    def _persist_vehicles(self, camera, detections):
        now = timezone.now()
        vehicles = [
            Vehicle(
                camera=camera,
                intersection=camera.intersection,
                vehicle_type=d['vehicle_type'],
                confidence_score=d['confidence_score'],
                bounding_box=d['bounding_box'],
                timestamp=now,
            )
            for d in detections
        ]
        if vehicles:
            Vehicle.objects.bulk_create(vehicles)

        emergency = next((d for d in detections if d['vehicle_type'] in (
            Vehicle.VehicleType.AMBULANCE, Vehicle.VehicleType.POLICE)), None)
        if emergency:
            self._broadcast_emergency(camera, emergency)
            # Signal Management module (added in this phase): force the
            # intersection's signal green immediately rather than waiting for
            # the next optimizer pass, which could be up to
            # OPTIMIZE_INTERVAL_SECONDS away.
            from signals_app.optimizer import trigger_emergency_priority
            trigger_emergency_priority(camera.intersection, emergency['vehicle_type'])

    def _flush_snapshot(self, camera):
        vehicle_count = len(self._recent_detections)
        congestion_level = _congestion_level(vehicle_count)
        avg_waiting_time = _estimate_waiting_time(vehicle_count)
        # Queue length is approximated from count; a calibrated per-camera
        # pixels-to-metres factor can replace this once cameras are surveyed.
        queue_length_meters = round(vehicle_count * 5.5, 1)

        snapshot = TrafficDensitySnapshot.objects.create(
            intersection=camera.intersection,
            vehicle_count=vehicle_count,
            queue_length_meters=queue_length_meters,
            avg_waiting_time_seconds=avg_waiting_time,
            congestion_level=congestion_level,
            captured_at=timezone.now(),
        )
        self._broadcast_update(camera, snapshot)
        self._recent_detections = []
        self._last_snapshot_at = time.monotonic()

    def _broadcast_update(self, camera, snapshot):
        payload = {
            'type': 'monitoring.update',
            'intersection_id': str(camera.intersection_id),
            'intersection_name': camera.intersection.name,
            'camera_id': str(camera.id),
            'vehicle_count': snapshot.vehicle_count,
            'queue_length_meters': snapshot.queue_length_meters,
            'avg_waiting_time_seconds': snapshot.avg_waiting_time_seconds,
            'congestion_level': snapshot.congestion_level,
            'captured_at': snapshot.captured_at.isoformat(),
        }
        self._group_send(OVERVIEW_GROUP, payload)
        self._group_send(intersection_group_name(camera.intersection_id), payload)

    def _broadcast_emergency(self, camera, detection):
        payload = {
            'type': 'emergency.alert',
            'intersection_id': str(camera.intersection_id),
            'intersection_name': camera.intersection.name,
            'camera_id': str(camera.id),
            'vehicle_type': detection['vehicle_type'],
            'confidence_score': detection['confidence_score'],
            'detected_at': timezone.now().isoformat(),
        }
        self._group_send(OVERVIEW_GROUP, payload)
        self._group_send(intersection_group_name(camera.intersection_id), payload)

    def _group_send(self, group_name, payload):
        async_to_sync(self.channel_layer.group_send)(group_name, {
            'type': payload['type'].replace('.', '_'),
            'payload': payload,
        })

    @staticmethod
    def _set_camera_status(camera, status):
        Camera.objects.filter(pk=camera.pk).update(status=status)

    @staticmethod
    def _heartbeat(camera):
        Camera.objects.filter(pk=camera.pk).update(last_heartbeat=timezone.now())
