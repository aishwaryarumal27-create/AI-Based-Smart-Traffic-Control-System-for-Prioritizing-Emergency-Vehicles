"""
analytics.py — Real-time traffic analytics engine
"""

import json
import os
import time
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Any
import threading
import numpy as np
from traffic_history import traffic_history

class TrafficAnalytics:
    def __init__(self, history_minutes: int = 60):
        self.history_minutes = history_minutes
        self.data_lock = threading.Lock()
        
        # Real-time counters
        self.total_vehicles = 0
        self.vehicle_types = defaultdict(int)
        self.emergency_count = 0
        self.emergency_logs = []
        
        # Per-camera data
        self.camera_data = {
            0: {"name": "North", "count": 0, "waiting_time": 0, "density": 0, "history": deque(maxlen=360)},
            1: {"name": "East", "count": 0, "waiting_time": 0, "density": 0, "history": deque(maxlen=360)},
            2: {"name": "South", "count": 0, "waiting_time": 0, "density": 0, "history": deque(maxlen=360)},
            3: {"name": "West", "count": 0, "waiting_time": 0, "density": 0, "history": deque(maxlen=360)},
        }
        
        # Time-series data
        self.traffic_history = deque(maxlen=history_minutes * 60)  # seconds
        self.hourly_density = defaultdict(list)
        self.peak_hours = []
        
        # Signal analytics
        self.signal_changes = []
        self.emergency_overrides = 0
        self.green_durations = []
        
        # Waiting times
        self.waiting_times = defaultdict(list)
        self.avg_waiting_time = 0
        
        # History file
        self.history_file = "traffic_history.json"
        self.load_history()
        
        # Start background analytics
        self.running = True
        self.analytics_thread = threading.Thread(target=self._background_analytics, daemon=True)
        self.analytics_thread.start()
    
    def _background_analytics(self):
        """Background thread for periodic analytics"""
        while self.running:
            time.sleep(5)
            self.calculate_peak_hours()
            self.calculate_average_waiting_time()
            self.save_history()
    
    def update_detection(self, cam_id: int, vehicle_type: str, is_emergency: bool, 
                         eta: int, signal_state: str, timestamp: float = None):
        """Update analytics with new detection"""
        if timestamp is None:
            timestamp = time.time()
        
        with self.data_lock:
            self.total_vehicles += 1
            self.vehicle_types[vehicle_type] += 1
            
            # Update camera count
            self.camera_data[cam_id]["count"] += 1
            
            # Track hourly density
            hour = datetime.fromtimestamp(timestamp).strftime("%H:00")
            self.hourly_density[hour].append(1)
            
            # Add to time series
            self.traffic_history.append({
                "timestamp": timestamp,
                "cam_id": cam_id,
                "type": vehicle_type,
                "is_emergency": is_emergency,
                "eta": eta,
                "signal": signal_state
            })
            
            # Emergency tracking
            if is_emergency:
                self.emergency_count += 1
                self.emergency_logs.insert(0, {
                    "timestamp": datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                    "camera": self.camera_data[cam_id]["name"],
                    "cam_id": cam_id,
                    "vehicle_type": vehicle_type,
                    "eta": eta,
                    "signal_priority": "Activated"
                })
                # Keep only last 100 emergency logs
                self.emergency_logs = self.emergency_logs[:100]
            
            # Calculate waiting time based on signal state
            if signal_state == "RED":
                wait_time = self._estimate_waiting_time(cam_id)
                self.waiting_times[cam_id].append(wait_time)
        # Save snapshot every 100 detections
        if self.total_vehicles % 100 == 0:
         traffic_history.add_snapshot(self.get_dashboard_data())
    
    def _estimate_waiting_time(self, cam_id: int) -> int:
        """Estimate waiting time based on vehicle queue"""
        # Simple estimation: more vehicles = longer wait
        queue_length = self.camera_data[cam_id]["count"] % 20
        base_wait = 10
        return base_wait + (queue_length // 3)
    
    def update_signal_change(self, direction: str, green_duration: int, is_emergency_override: bool = False):
        """Record signal change for analytics"""
        with self.data_lock:
            self.signal_changes.append({
                "timestamp": time.time(),
                "direction": direction,
                "duration": green_duration,
                "emergency_override": is_emergency_override
            })
            
            if green_duration > 0:
                self.green_durations.append(green_duration)
            
            if is_emergency_override:
                self.emergency_overrides += 1
    
    def update_camera_density(self, cam_id: int, vehicle_count: int, max_vehicles: int = 15):
        """Update traffic density for a camera"""
        with self.data_lock:
            density = min(100, (vehicle_count / max_vehicles) * 100)
            self.camera_data[cam_id]["density"] = density
            self.camera_data[cam_id]["history"].append({
                "timestamp": time.time(),
                "density": density,
                "count": vehicle_count
            })
    
    def calculate_peak_hours(self):
        """Analyze and identify peak traffic hours"""
        with self.data_lock:
            if not self.hourly_density:
                return
            
            # Calculate average density per hour
            hourly_avg = {}
            for hour, densities in self.hourly_density.items():
                hourly_avg[hour] = len(densities) / max(1, len(set([int(d) for d in densities])))
            
            # Identify top 3 peak hours
            sorted_hours = sorted(hourly_avg.items(), key=lambda x: x[1], reverse=True)
            self.peak_hours = [{"hour": h, "density": round(d, 2)} for h, d in sorted_hours[:3]]
    
    def calculate_average_waiting_time(self):
        """Calculate average waiting time across all lanes"""
        with self.data_lock:
            all_times = []
            for times in self.waiting_times.values():
                all_times.extend(times)
            
            if all_times:
                self.avg_waiting_time = round(np.mean(all_times), 1)
            else:
                self.avg_waiting_time = 0
    
    def get_congestion_level(self, cam_id: int) -> str:
        """Get congestion level for a camera"""
        density = self.camera_data[cam_id]["density"]
        if density < 30:
            return "LOW"
        elif density < 70:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def get_congestion_color(self, cam_id: int) -> str:
        """Get color for congestion heatmap"""
        level = self.get_congestion_level(cam_id)
        colors = {"LOW": "#00ff88", "MEDIUM": "#ffcc00", "HIGH": "#ff3355"}
        return colors.get(level, "#4a6070")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard analytics data"""
        with self.data_lock:
            # Calculate per-camera stats
            cameras = []
            for cam_id, data in self.camera_data.items():
                cameras.append({
                    "id": cam_id,
                    "name": data["name"],
                    "count": data["count"],
                    "density": round(data["density"], 1),
                    "congestion": self.get_congestion_level(cam_id),
                    "color": self.get_congestion_color(cam_id),
                    "waiting_time": round(np.mean(self.waiting_times.get(cam_id, [10])), 1)
                })
            
            # Find busiest camera
            busiest = max(cameras, key=lambda x: x["count"]) if cameras else None
            
            # Prepare time series data for charts
            time_labels = []
            vehicle_counts = []
            densities = []
            
            # Last 30 minutes of data (sample every minute)
            now = time.time()
            for i in range(30, 0, -1):
                minute_ago = now - (i * 60)
                time_labels.append(datetime.fromtimestamp(minute_ago).strftime("%H:%M"))
                
                # Count vehicles in this minute
                count = sum(1 for t in self.traffic_history 
                           if t["timestamp"] >= minute_ago - 60 and t["timestamp"] < minute_ago)
                vehicle_counts.append(count)
                
                # Average density
                avg_density = np.mean([c["density"] for c in cameras]) if cameras else 0
                densities.append(round(avg_density, 1))
            
            # Emergency vehicles by type
            emergency_by_camera = defaultdict(int)
            for log in self.emergency_logs[:50]:
                emergency_by_camera[log["camera"]] += 1
            
            # Signal efficiency
            avg_green_duration = np.mean(self.green_durations) if self.green_durations else 12
            signal_efficiency = min(100, (avg_green_duration / 15) * 100)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(cameras)
            
            # Congestion heatmap data
            heatmap_data = {
                "North": self.camera_data[0]["density"],
                "East": self.camera_data[1]["density"],
                "South": self.camera_data[2]["density"],
                "West": self.camera_data[3]["density"]
            }
            
            return {
                "total_vehicles": self.total_vehicles,
                "vehicle_types": dict(self.vehicle_types),
                "emergency_count": self.emergency_count,
                "emergency_logs": self.emergency_logs[:20],
                "cameras": cameras,
                "busiest_camera": busiest,
                "peak_hours": self.peak_hours,
                "avg_waiting_time": self.avg_waiting_time,
                "emergency_overrides": self.emergency_overrides,
                "signal_efficiency": round(signal_efficiency, 1),
                "avg_green_duration": round(avg_green_duration, 1),
                "time_labels": time_labels,
                "vehicle_counts": vehicle_counts,
                "density_history": densities,
                "emergency_by_camera": dict(emergency_by_camera),
                "recommendations": recommendations,
                "heatmap_data": heatmap_data,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        # Add history statistics
        history_stats = traffic_history.get_statistics()
        result["history_stats"] = history_stats
        result["hourly_pattern"] = traffic_history.get_hourly_pattern()
        result["trend_analysis"] = traffic_history.get_trend_analysis()
    
    def _generate_recommendations(self, cameras: List[Dict]) -> List[str]:
        """Generate smart recommendations based on analytics"""
        recommendations = []
        
        for cam in cameras:
            if cam["congestion"] == "HIGH" and cam["density"] > 80:
                recommendations.append(f"⚠️ Heavy congestion detected in {cam['name']} lane. Consider increasing green signal duration.")
            elif cam["congestion"] == "MEDIUM" and cam["density"] > 50:
                recommendations.append(f"📊 Moderate traffic in {cam['name']} lane. Monitor closely.")
        
        if self.avg_waiting_time > 25:
            recommendations.append(f"⏱️ Average waiting time is high ({self.avg_waiting_time}s). Optimize signal timing.")
        
        if self.emergency_overrides > 5:
            recommendations.append("🚑 Multiple emergency overrides detected. Consider dedicated emergency lane.")
        
        if not recommendations:
            recommendations.append("✅ Traffic flow is optimal. System running efficiently.")
        
        return recommendations[:4]
    
    def save_history(self):
        """Save analytics history to file"""
        try:
            data = {
                "total_vehicles": self.total_vehicles,
                "vehicle_types": dict(self.vehicle_types),
                "emergency_count": self.emergency_count,
                "timestamp": time.time()
            }
            with open(self.history_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def load_history(self):
        """Load analytics history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, "r") as f:
                    data = json.load(f)
                    self.total_vehicles = data.get("total_vehicles", 0)
                    self.vehicle_types = defaultdict(int, data.get("vehicle_types", {}))
                    self.emergency_count = data.get("emergency_count", 0)
        except Exception as e:
            print(f"Error loading history: {e}")
    
    def reset(self):
        """Reset all analytics (for testing)"""
        with self.data_lock:
            self.total_vehicles = 0
            self.vehicle_types.clear()
            self.emergency_count = 0
            self.emergency_logs.clear()
            self.waiting_times.clear()
            self.green_durations.clear()
            self.emergency_overrides = 0
            for cam_id in self.camera_data:
                self.camera_data[cam_id]["count"] = 0
                self.camera_data[cam_id]["density"] = 0
                self.camera_data[cam_id]["history"].clear()
    
    def stop(self):
        """Stop background analytics"""
        self.running = False


# Global analytics instance
analytics = TrafficAnalytics()