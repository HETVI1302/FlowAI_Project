"""
Thin wrapper around a YOLOv8 model, mapping COCO classes to FlowAI's
Vehicle.VehicleType choices. Kept separate from pipeline.py so the model
can be unit-tested (or swapped for a fine-tuned weights file that also
distinguishes ambulance/police liveries) without touching the streaming
/ persistence / broadcast logic.

Import of `ultralytics` and `cv2` is deferred into __init__ rather than
module level: this file is imported by Django's app registry indirectly
(via management commands), and we don't want a missing/broken CV
dependency to break `manage.py` for people just working on the web app.
"""
from django.conf import settings

from monitoring.models import Vehicle

# COCO class id -> FlowAI vehicle type. YOLOv8's stock weights don't know
# "ambulance" or "police vehicle" as distinct classes — those are inferred
# downstream from livery colour/markings by a fine-tuned head when
# available; until that model is swapped in, they surface as CAR/TRUCK and
# get corrected via the manual "mark as emergency" operator action.
COCO_TO_VEHICLE_TYPE = {
    2: Vehicle.VehicleType.CAR,
    3: Vehicle.VehicleType.MOTORCYCLE,
    5: Vehicle.VehicleType.BUS,
    7: Vehicle.VehicleType.TRUCK,
}

DEFAULT_CONFIDENCE_THRESHOLD = 0.4


class VehicleDetector:
    """Loads a YOLOv8 model once per worker process and runs inference on frames."""

    def __init__(self, weights_path=None, confidence_threshold=None, device=None):
        try:
            from ultralytics import YOLO
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError(
                'ultralytics is not installed. Run '
                '`pip install ultralytics --break-system-packages` to enable '
                'live vehicle detection.'
            ) from exc

        self.weights_path = weights_path or getattr(settings, 'YOLO_WEIGHTS_PATH', 'yolov8n.pt')
        self.confidence_threshold = confidence_threshold or getattr(
            settings, 'YOLO_CONFIDENCE_THRESHOLD', DEFAULT_CONFIDENCE_THRESHOLD
        )
        self.device = device or getattr(settings, 'YOLO_DEVICE', 'cpu')
        self.model = YOLO(self.weights_path)

    def detect(self, frame):
        """
        Run inference on a single BGR frame (numpy array from cv2.VideoCapture).
        Returns a list of dicts: vehicle_type, confidence_score, bounding_box.
        Non-vehicle COCO classes and below-threshold detections are dropped.
        """
        results = self.model.predict(
            source=frame,
            device=self.device,
            conf=self.confidence_threshold,
            verbose=False,
        )

        detections = []
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                class_id = int(box.cls[0])
                vehicle_type = COCO_TO_VEHICLE_TYPE.get(class_id)
                if vehicle_type is None:
                    continue  # not a vehicle class (pedestrian, traffic light, etc.)
                x_min, y_min, x_max, y_max = (float(v) for v in box.xyxy[0])
                detections.append({
                    'vehicle_type': vehicle_type,
                    'confidence_score': float(box.conf[0]),
                    'bounding_box': [x_min, y_min, x_max, y_max],
                })
        return detections
