import cv2
import numpy as np
import time
from ultralytics import YOLO

class TrafficAIEngine:
    def __init__(self, model_path='yolov8n.pt'):
        """
        Initialize the YOLOv8 model for vehicle detection.
        Downloads yolov8n.pt automatically if it doesn't exist.
        """
        self.model = YOLO(model_path)
        # COCO dataset classes for vehicles
        self.vehicle_classes = {
            2: 'car',
            3: 'motorcycle',
            5: 'bus',
            7: 'truck'
        }
        # Emergency vehicles are not explicitly in standard COCO, 
        # so this is a simplified mapping or would require a custom model.
        # For demonstration, we map specific classes.

    def process_frame(self, frame):
        """
        Process a single frame to detect vehicles.
        Returns the annotated frame and a list of detections.
        """
        results = self.model(frame, classes=list(self.vehicle_classes.keys()), conf=0.3)
        detections = []
        
        annotated_frame = frame.copy()
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                vehicle_type = self.vehicle_classes.get(cls_id, 'unknown')
                
                # Bounding box coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Append to detections list
                detections.append({
                    'type': vehicle_type,
                    'confidence': conf,
                    'bbox': (x1, y1, x2, y2)
                })
                
                # Draw bounding box on frame
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(annotated_frame, f"{vehicle_type} {conf:.2f}", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            
        return annotated_frame, detections

    def calculate_density(self, detections, area_size):
        """
        Calculate traffic density based on number of vehicles and area.
        """
        vehicle_count = len(detections)
        if area_size <= 0:
            return 0
        return vehicle_count / area_size
