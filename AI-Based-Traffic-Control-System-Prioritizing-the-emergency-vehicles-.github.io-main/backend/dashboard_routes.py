"""
dashboard_routes.py — FastAPI routes for analytics dashboard
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from typing import List, Dict, Any
import json
import io
import csv
from datetime import datetime

from analytics import analytics
from report_export import ReportExporter

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

# WebSocket connections for dashboard
dashboard_clients = []


@router.get("/analytics")
async def get_analytics():
    """Get current analytics data"""
    return analytics.get_dashboard_data()


@router.get("/export/csv")
async def export_csv():
    """Export analytics data as CSV"""
    data = analytics.get_dashboard_data()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(["Report Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])
    
    # Summary
    writer.writerow(["SUMMARY STATISTICS"])
    writer.writerow(["Total Vehicles", data["total_vehicles"]])
    writer.writerow(["Emergency Vehicles", data["emergency_count"]])
    writer.writerow(["Emergency Overrides", data["emergency_overrides"]])
    writer.writerow(["Average Waiting Time (s)", data["avg_waiting_time"]])
    writer.writerow(["Signal Efficiency (%)", data["signal_efficiency"]])
    writer.writerow([])
    
    # Vehicle types
    writer.writerow(["VEHICLE TYPE BREAKDOWN"])
    writer.writerow(["Type", "Count"])
    for vtype, count in data["vehicle_types"].items():
        writer.writerow([vtype, count])
    writer.writerow([])
    
    # Per-camera data
    writer.writerow(["CAMERA STATISTICS"])
    writer.writerow(["Camera", "Vehicle Count", "Density (%)", "Congestion", "Waiting Time (s)"])
    for cam in data["cameras"]:
        writer.writerow([cam["name"], cam["count"], cam["density"], cam["congestion"], cam["waiting_time"]])
    writer.writerow([])
    
    # Emergency logs
    writer.writerow(["EMERGENCY VEHICLE LOGS"])
    writer.writerow(["Timestamp", "Camera", "Vehicle Type", "ETA (s)", "Priority"])
    for log in data["emergency_logs"]:
        writer.writerow([log["timestamp"], log["camera"], log["vehicle_type"], log["eta"], log["signal_priority"]])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=traffic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )


@router.get("/export/pdf")
async def export_pdf():
    """Export analytics data as PDF"""
    exporter = ReportExporter()
    pdf_bytes = exporter.generate_pdf_report(analytics.get_dashboard_data())
    
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=traffic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"}
    )


@router.post("/reset")
async def reset_analytics():
    """Reset analytics data"""
    analytics.reset()
    return {"status": "reset"}


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket for real-time dashboard updates"""
    await websocket.accept()
    dashboard_clients.append(websocket)
    
    try:
        while True:
            # Keep connection alive and send updates every 2 seconds
            await websocket.receive_text()
    except WebSocketDisconnect:
        dashboard_clients.remove(websocket)


async def broadcast_dashboard_update():
    """Broadcast analytics update to all dashboard clients"""
    if not dashboard_clients:
        return
    
    data = analytics.get_dashboard_data()
    message = json.dumps({
        "type": "analytics_update",
        "data": data
    })
    
    dead_clients = []
    for client in dashboard_clients:
        try:
            await client.send_text(message)
        except:
            dead_clients.append(client)
    
    for dead in dead_clients:
        if dead in dashboard_clients:
            dashboard_clients.remove(dead)