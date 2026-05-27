from ultralytics import YOLO
import torch
import cv2
import base64
from ultralytics.nn.tasks import DetectionModel

#
torch.set_grad_enabled(False)

VEHICLE_CLASSES = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

CONFIDENCE_THRESHOLD = 0.40
AMBULANCE_CONFIDENCE = 0.50


class VehicleDetector:

    def __init__(self):

        try:

            # NORMAL VEHICLE MODEL
            self.vehicle_model = YOLO("models/yolov8n.pt")

            # AMBULANCE MODELS
            self.ambulance_model1 = YOLO("models/best1.pt")
            self.ambulance_model2 = YOLO("models/best2.pt")
            self.ambulance_model3 = YOLO("models/best3.pt")

            print("✅ All models loaded")

        except Exception as e:

            print("❌ Model loading failed:", e)
            raise e

    # ─────────────────────────────
    # 🚑 FULL FRAME AMBULANCE DETECTION
    # ─────────────────────────────
    def detect_ambulances(self, frame):

        ambulance_boxes = []

        models = [
            self.ambulance_model1,
            self.ambulance_model2,
            self.ambulance_model3
        ]

        for model in models:

            try:

                results = model(
                    frame,
                    verbose=False
                )[0]

                if results.boxes is None:
                    continue

                for box in results.boxes:

                    conf = float(box.conf[0])

                    cls_id = int(box.cls[0])

                    label = model.names[cls_id].lower()

                    if (
                        label == "ambulance"
                        and conf > AMBULANCE_CONFIDENCE
                    ):

                        x1, y1, x2, y2 = map(
                            int,
                            box.xyxy[0].tolist()
                        )

                        ambulance_boxes.append({
                            "bbox": [x1, y1, x2, y2],
                            "confidence": conf
                        })

            except Exception as e:

                print("❌ Ambulance detection error:", e)

        return ambulance_boxes

    # ─────────────────────────────
    # 🚗 MAIN DETECTION
    # ─────────────────────────────
    def detect(self, frame):

        detections = []

        # NORMAL VEHICLES
        try:

            vehicle_results = self.vehicle_model(
                frame,
                verbose=False
            )[0]

        except Exception as e:

            print("❌ Vehicle detection error:", e)

            return []

        # AMBULANCE DETECTION
        ambulance_boxes = self.detect_ambulances(frame)

        # ─────────────────────────────
        # ADD NORMAL VEHICLES
        # ─────────────────────────────
        if vehicle_results.boxes is not None:

            for box in vehicle_results.boxes:

                try:

                    conf = float(box.conf[0])

                    cls_id = int(box.cls[0])

                    if cls_id not in VEHICLE_CLASSES:
                        continue

                    if conf < CONFIDENCE_THRESHOLD:
                        continue

                    x1, y1, x2, y2 = map(
                        int,
                        box.xyxy[0].tolist()
                    )

                    class_name = VEHICLE_CLASSES[cls_id]

                    detections.append({
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(conf, 2),
                        "class_name": class_name,
                        "is_emergency": False
                    })

                except Exception:
                    continue

        # ─────────────────────────────
        # ADD AMBULANCES
        # ─────────────────────────────
        for amb in ambulance_boxes:

            x1, y1, x2, y2 = amb["bbox"]

            detections.append({
                "bbox": [x1, y1, x2, y2],
                "confidence": round(amb["confidence"], 2),
                "class_name": "ambulance",
                "is_emergency": True
            })

            print("🚑 AMBULANCE DETECTED")

        return detections

    # ─────────────────────────────
    # 🎨 DRAW
    # ─────────────────────────────
    def draw_detections(self, frame, detections):

        for det in detections:

            x1, y1, x2, y2 = det["bbox"]

            label = det["class_name"]

            conf = det["confidence"]

            is_emergency = det["is_emergency"]

            color = (0, 255, 0)

            if is_emergency:
                color = (0, 0, 255)

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            text = f"{label} {conf}"

            if is_emergency:
                text = f"🚑 AMBULANCE {conf}"

            cv2.putText(
                frame,
                text,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

        return frame


def frame_to_base64(frame, quality=70):

    try:

        _, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        )

        return base64.b64encode(
            buffer
        ).decode("utf-8")

    except Exception as e:

        print("❌ Frame encode error:", e)

        return ""
