import csv
from datetime import datetime


class TrafficModel:
    """Adjusts travel time based on time-of-day traffic multipliers."""

    def __init__(self, filename="data/traffic_profile.csv"):
        self.profile = {}
        self._load(filename)

    def _load(self, filename):
        try:
            with open(filename, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self.profile[row["road_type"]] = {
                        "06-10": float(row["06-10"]),
                        "10-16": float(row["10-16"]),
                        "16-20": float(row["16-20"]),
                        "20-06": float(row["20-06"]),
                    }
        except FileNotFoundError:
            # fallback: no traffic
            self.profile = {}

    def _slot(self, hour):
        if 6 <= hour < 10:  return "06-10"
        if 10 <= hour < 16: return "10-16"
        if 16 <= hour < 20: return "16-20"
        return "20-06"

    def multiplier(self, road_type, hour=None):
        if hour is None:
            hour = datetime.now().hour
        slot = self._slot(hour)
        return self.profile.get(road_type, {}).get(slot, 1.0)

    def travel_time(self, distance, speed, road_type, hour=None):
        """Returns minutes after applying traffic."""
        base = (distance / speed) * 60
        return base * self.multiplier(road_type, hour)