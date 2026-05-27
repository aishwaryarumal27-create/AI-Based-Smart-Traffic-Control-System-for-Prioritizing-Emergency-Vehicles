"""
traffic_history.py — Traffic history storage and retrieval module
"""

import json
import os
import csv
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
import threading
import time


class TrafficHistory:
    """Manages storage and retrieval of traffic analytics history"""
    
    def __init__(self, history_dir: str = "traffic_history"):
        self.history_dir = history_dir
        self.data_lock = threading.Lock()
        self.history_data = []
        self.daily_summaries = []
        
        # Create history directory if it doesn't exist
        os.makedirs(history_dir, exist_ok=True)
        
        # Load existing history
        self.load_history()
        
        # Start background saver
        self.running = True
        self.saver_thread = threading.Thread(target=self._background_saver, daemon=True)
        self.saver_thread.start()
    
    def _background_saver(self):
        """Background thread to periodically save history"""
        while self.running:
            time.sleep(60)  # Save every minute
            self.save_history()
    
    def add_record(self, record: Dict[str, Any]):
        """Add a single record to history"""
        with self.data_lock:
            # Add timestamp if not present
            if "timestamp" not in record:
                record["timestamp"] = time.time()
            
            # Add human-readable datetime
            if "datetime" not in record:
                record["datetime"] = datetime.fromtimestamp(record["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            
            self.history_data.append(record)
            
            # Keep only last 7 days of data (604800 seconds)
            cutoff_time = time.time() - (7 * 24 * 3600)
            self.history_data = [r for r in self.history_data if r.get("timestamp", 0) > cutoff_time]
    
    def add_snapshot(self, analytics_data: Dict[str, Any]):
        """Add a complete analytics snapshot to history"""
        snapshot = {
            "timestamp": time.time(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_vehicles": analytics_data.get("total_vehicles", 0),
            "emergency_count": analytics_data.get("emergency_count", 0),
            "avg_waiting_time": analytics_data.get("avg_waiting_time", 0),
            "signal_efficiency": analytics_data.get("signal_efficiency", 0),
            "emergency_overrides": analytics_data.get("emergency_overrides", 0),
            "cameras": analytics_data.get("cameras", []),
            "vehicle_types": analytics_data.get("vehicle_types", {}),
            "peak_hours": analytics_data.get("peak_hours", [])
        }
        self.add_record(snapshot)
    
    def get_history(self, hours: int = 24) -> List[Dict]:
        """Get history for last N hours"""
        cutoff_time = time.time() - (hours * 3600)
        with self.data_lock:
            return [r for r in self.history_data if r.get("timestamp", 0) > cutoff_time]
    
    def get_daily_summary(self, date: Optional[str] = None) -> Dict:
        """Get daily summary for a specific date"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        with self.data_lock:
            day_records = [
                r for r in self.history_data 
                if r.get("datetime", "").startswith(date)
            ]
            
            if not day_records:
                return {"date": date, "total_vehicles": 0, "emergency_count": 0, "records": []}
            
            return {
                "date": date,
                "total_vehicles": sum(r.get("total_vehicles", 0) for r in day_records),
                "emergency_count": sum(r.get("emergency_count", 0) for r in day_records),
                "avg_waiting_time": sum(r.get("avg_waiting_time", 0) for r in day_records) / len(day_records),
                "signal_efficiency": sum(r.get("signal_efficiency", 0) for r in day_records) / len(day_records),
                "records": day_records
            }
    
    def get_weekly_summary(self) -> Dict:
        """Get weekly summary of traffic"""
        weekly_data = defaultdict(lambda: {
            "total_vehicles": 0,
            "emergency_count": 0,
            "waiting_times": [],
            "efficiencies": []
        })
        
        with self.data_lock:
            for record in self.history_data:
                date_str = record.get("datetime", "")[:10]
                if date_str:
                    weekly_data[date_str]["total_vehicles"] += record.get("total_vehicles", 0)
                    weekly_data[date_str]["emergency_count"] += record.get("emergency_count", 0)
                    weekly_data[date_str]["waiting_times"].append(record.get("avg_waiting_time", 0))
                    weekly_data[date_str]["efficiencies"].append(record.get("signal_efficiency", 0))
        
        # Calculate averages
        result = {}
        for date, data in weekly_data.items():
            result[date] = {
                "total_vehicles": data["total_vehicles"],
                "emergency_count": data["emergency_count"],
                "avg_waiting_time": sum(data["waiting_times"]) / len(data["waiting_times"]) if data["waiting_times"] else 0,
                "signal_efficiency": sum(data["efficiencies"]) / len(data["efficiencies"]) if data["efficiencies"] else 0
            }
        
        return result
    
    def get_hourly_pattern(self) -> Dict[str, float]:
        """Analyze hourly traffic patterns"""
        hourly_counts = defaultdict(list)
        
        with self.data_lock:
            for record in self.history_data:
                datetime_str = record.get("datetime", "")
                if datetime_str:
                    try:
                        hour = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S").strftime("%H:00")
                        hourly_counts[hour].append(record.get("total_vehicles", 0))
                    except:
                        pass
        
        # Calculate averages per hour
        hourly_avg = {}
        for hour, counts in hourly_counts.items():
            hourly_avg[hour] = sum(counts) / len(counts) if counts else 0
        
        return hourly_avg
    
    def get_trend_analysis(self) -> Dict:
        """Analyze traffic trends over time"""
        with self.data_lock:
            if len(self.history_data) < 10:
                return {"trend": "insufficient_data", "direction": "stable", "percentage": 0}
            
            # Get last 10 records for trend analysis
            recent = self.history_data[-10:]
            older = self.history_data[-20:-10] if len(self.history_data) >= 20 else self.history_data[:10]
            
            recent_avg = sum(r.get("total_vehicles", 0) for r in recent) / len(recent)
            older_avg = sum(r.get("total_vehicles", 0) for r in older) / len(older) if older else recent_avg
            
            if recent_avg > older_avg * 1.1:
                trend = "increasing"
                direction = "up"
                percentage = ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0
            elif recent_avg < older_avg * 0.9:
                trend = "decreasing"
                direction = "down"
                percentage = ((older_avg - recent_avg) / older_avg) * 100 if older_avg > 0 else 0
            else:
                trend = "stable"
                direction = "stable"
                percentage = 0
            
            return {
                "trend": trend,
                "direction": direction,
                "percentage": round(percentage, 1),
                "recent_average": round(recent_avg, 1),
                "older_average": round(older_avg, 1)
            }
    
    def export_to_csv(self, filename: Optional[str] = None) -> str:
        """Export history to CSV file"""
        if filename is None:
            filename = os.path.join(self.history_dir, f"traffic_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        with self.data_lock:
            if not self.history_data:
                return ""
            
            # Get all unique keys
            all_keys = set()
            for record in self.history_data:
                all_keys.update(record.keys())
            
            with open(filename, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(self.history_data)
        
        return filename
    
    def save_history(self):
        """Save history to JSON file"""
        filename = os.path.join(self.history_dir, f"history_{datetime.now().strftime('%Y%m%d')}.json")
        
        with self.data_lock:
            # Load existing data for today
            existing_data = []
            if os.path.exists(filename):
                try:
                    with open(filename, 'r') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = []
            
            # Merge with new data (avoid duplicates)
            existing_timestamps = {r.get("timestamp") for r in existing_data}
            new_records = [r for r in self.history_data if r.get("timestamp") not in existing_timestamps]
            
            all_records = existing_data + new_records
            
            # Save to file
            with open(filename, 'w') as f:
                json.dump(all_records, f, indent=2)
    
    def load_history(self):
        """Load history from JSON files"""
        # Load today's history file
        filename = os.path.join(self.history_dir, f"history_{datetime.now().strftime('%Y%m%d')}.json")
        
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    loaded_data = json.load(f)
                    with self.data_lock:
                        self.history_data = loaded_data
            except Exception as e:
                print(f"Error loading history: {e}")
                self.history_data = []
    
    def clear_old_history(self, days_to_keep: int = 7):
        """Delete history older than specified days"""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        with self.data_lock:
            self.history_data = [r for r in self.history_data if r.get("timestamp", 0) > cutoff_time]
        
        # Also delete old JSON files
        for filename in os.listdir(self.history_dir):
            if filename.startswith("history_") and filename.endswith(".json"):
                try:
                    date_str = filename.replace("history_", "").replace(".json", "")
                    file_date = datetime.strptime(date_str, "%Y%m%d")
                    if (datetime.now() - file_date).days > days_to_keep:
                        os.remove(os.path.join(self.history_dir, filename))
                except:
                    pass
    
    def get_statistics(self) -> Dict:
        """Get comprehensive statistics from history"""
        with self.data_lock:
            if not self.history_data:
                return {"error": "No historical data available"}
            
            total_vehicles = sum(r.get("total_vehicles", 0) for r in self.history_data)
            total_emergencies = sum(r.get("emergency_count", 0) for r in self.history_data)
            
            avg_waiting = [r.get("avg_waiting_time", 0) for r in self.history_data if r.get("avg_waiting_time", 0) > 0]
            avg_efficiency = [r.get("signal_efficiency", 0) for r in self.history_data if r.get("signal_efficiency", 0) > 0]
            
            return {
                "total_records": len(self.history_data),
                "total_vehicles_historical": total_vehicles,
                "total_emergencies_historical": total_emergencies,
                "avg_waiting_time_historical": sum(avg_waiting) / len(avg_waiting) if avg_waiting else 0,
                "avg_signal_efficiency_historical": sum(avg_efficiency) / len(avg_efficiency) if avg_efficiency else 0,
                "first_record": self.history_data[0].get("datetime") if self.history_data else None,
                "last_record": self.history_data[-1].get("datetime") if self.history_data else None
            }
    
    def stop(self):
        """Stop background processes"""
        self.running = False
        self.save_history()


# Global history instance
traffic_history = TrafficHistory()