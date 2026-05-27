import asyncio
import json
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from detection import VehicleDetector
from tracker import CentroidTracker
from eta import ETACalculator
from report import ReportGenerator

# Add these imports at the top
from dashboard_routes import router as dashboard_router
from analytics import analytics
from congestion_predictor import predictor

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
VIDEO_DIR = FRONTEND_DIR / "videos"

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add these routes after your existing routes
app.include_router(dashboard_router)

# Add this endpoint to serve dashboard page
@app.get("/dashboard")
async def dashboard():
    return FileResponse(str(FRONTEND_DIR / "dashboard.html"))

# ─────────────────────────────
# GLOBAL STATE
# ─────────────────────────────
processing_active = False
clients = []
clients_lock = asyncio.Lock()

VIDEO_FILES = [
    str(VIDEO_DIR / "video0.mp4"),
    str(VIDEO_DIR / "video1.mp4"),
    str(VIDEO_DIR / "video2.mp4"),
    str(VIDEO_DIR / "video3.mp4"),
]

DIRECTIONS = ["North", "East", "South", "West"]

signal_state = {d: "RED" for d in DIRECTIONS}
signal_index = 0
last_switch = time.time()

SIGNAL_DURATION = 10  # seconds

signal_timer = {
    "active": "North",
    "time_remaining": SIGNAL_DURATION,
    "next": "East"
}

camera_data = {i: {} for i in range(4)}
camera_emergency = [0] * 4  # 🔥 stable tracking

detector = VehicleDetector()
trackers = [CentroidTracker() for _ in range(4)]
etas = [ETACalculator() for _ in range(4)]

logs = []
reporter = ReportGenerator()

def log(msg):
    logs.insert(0, f"{datetime.now().strftime('%H:%M:%S')} {msg}")
    if len(logs) > 50:
        logs.pop()

# ─────────────────────────────
# ✅ FIXED SIGNAL SYSTEM
# ─────────────────────────────
def update_signals():
    global signal_index, last_switch

    now = time.time()
    elapsed = now - last_switch

    # 🚨 EMERGENCY OVERRIDE
    for i, val in enumerate(camera_emergency):
        if val == 1:
            for j, d in enumerate(DIRECTIONS):
                signal_state[d] = "GREEN" if j == i else "RED"

            signal_timer["active"] = DIRECTIONS[i]
            signal_timer["time_remaining"] = SIGNAL_DURATION
            signal_timer["next"] = DIRECTIONS[(i + 1) % 4]
            return

    # 🔄 NORMAL ROTATION
    if elapsed >= SIGNAL_DURATION:
        signal_index = (signal_index + 1) % 4
        last_switch = now
        elapsed = 0  # reset properly

    for i, d in enumerate(DIRECTIONS):
        signal_state[d] = "GREEN" if i == signal_index else "RED"

    remaining = int(SIGNAL_DURATION - elapsed)
    if remaining < 0:
        remaining = 0

    signal_timer["active"] = DIRECTIONS[signal_index]
    signal_timer["time_remaining"] = remaining
    signal_timer["next"] = DIRECTIONS[(signal_index + 1) % 4]
    
    # Log signal change
    from analytics import analytics
    analytics.update_signal_change(
        direction=DIRECTIONS[signal_index],
        green_duration=SIGNAL_DURATION,
        is_emergency_override=any(camera_emergency)
    )

# ─────────────────────────────
# BROADCAST LOOP
# ─────────────────────────────
async def broadcast_all():
    while True:
        if processing_active:
            update_signals()

            payload = {
                "type": "update",
                "cameras": camera_data,
                "signals": signal_state,
                "signal_timer": signal_timer,
                "logs": logs[:10]
            }

            msg = json.dumps(payload)

            dead = []
            async with clients_lock:
                for ws in clients:
                    try:
                        await ws.send_text(msg)
                    except:
                        dead.append(ws)

                for d in dead:
                    clients.remove(d)
            
            # Also broadcast to dashboard clients
            from dashboard_routes import broadcast_dashboard_update
            await broadcast_dashboard_update()

        await asyncio.sleep(0.07)  # smooth FPS

# ─────────────────────────────
# CAMERA THREAD
# ─────────────────────────────
def process_camera(cam_id, video_path):
    global processing_active

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"VIDEO NOT OPENING: {video_path}")
        log(f"❌ Camera {cam_id} failed")
        return

    while processing_active:
        ret, frame = cap.read()

        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        frame = cv2.resize(frame, (416, 234))

        detections = detector.detect(frame)

        vehicles = []
        emergency = False
        emergency_info = None

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            conf = det["confidence"]
            label = det["class_name"]
            is_emergency = det["is_emergency"]

            eta = etas[cam_id].calculate((x1+x2)//2, (y1+y2)//2, label)

            color = (0,255,0) if not is_emergency else (0,0,255)

            cv2.rectangle(frame, (x1,y1), (x2,y2), color, 2)
            cv2.putText(frame, f"{label} {conf}", (x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            if is_emergency:
                emergency = True
                emergency_info = {"type": label, "confidence": conf, "eta": eta}

            vehicles.append({
                "type": label,
                "confidence": conf,
                "eta": eta
            })

            reporter.record(
                cam_id=cam_id,
                vehicle_type=label,
                confidence=conf,
                is_emergency=is_emergency,
                eta=eta,
                signal_state=signal_state[DIRECTIONS[cam_id]]
            )
            
            # After processing detections, update analytics:
            analytics.update_detection(
                cam_id=cam_id,
                vehicle_type=label,
                is_emergency=is_emergency,
                eta=eta,
                signal_state=signal_state[DIRECTIONS[cam_id]]
            )

        # update global emergency
        camera_emergency[cam_id] = 1 if emergency else 0

        # Update camera density
        analytics.update_camera_density(cam_id, len(vehicles))
        
        # Update predictor
        predictor.add_data_point(cam_id, len(vehicles) * 100 / 15, len(vehicles))

        # encode frame
        _, buffer = cv2.imencode(".jpg", frame)
        import base64
        frame_b64 = base64.b64encode(buffer).decode()

        camera_data[cam_id] = {
            "cam_id": cam_id,
            "frame": frame_b64,
            "vehicles": vehicles,
            "vehicle_count": len(vehicles),
            "emergency": emergency,
            "emergency_info": emergency_info
        }

        time.sleep(0.12)

    cap.release()

# ─────────────────────────────
# ROUTES
# ─────────────────────────────
@app.get("/")
def root():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.post("/start")
async def start():
    global processing_active

    if processing_active:
        return {"status": "already"}

    processing_active = True

    for i in range(4):
        threading.Thread(
            target=process_camera,
            args=(i, VIDEO_FILES[i]),
            daemon=True
        ).start()

    log("🚀 Started")
    return {"status": "started"}

@app.post("/stop")
def stop():
    global processing_active

    processing_active = False

    # ✅ SAVE REPORT
    reporter.save()

    log("🛑 Stopped")
    return {"status": "stopped"}

@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()

    async with clients_lock:
        clients.append(websocket)

    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        async with clients_lock:
            clients.remove(websocket)

# ─────────────────────────────
# STARTUP
# ─────────────────────────────
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_all())

# ─────────────────────────────
# RUN
# ─────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
