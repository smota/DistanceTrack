import json
import os
from datetime import datetime
import hashlib

class CacheManager:
    def __init__(self, cache_dir=".cache"):
        self.cache_dir = cache_dir
        self.geocode_cache_file = os.path.join(cache_dir, "geocode_cache.json")
        self.route_cache_file = os.path.join(cache_dir, "route_cache.json")
        self._ensure_cache_dir()
        self._load_caches()

    def _ensure_cache_dir(self):
        """Ensure cache directory exists."""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def _load_caches(self):
        """Load both caches from files."""
        # Load geocode cache
        if os.path.exists(self.geocode_cache_file):
            with open(self.geocode_cache_file, 'r') as f:
                self.geocode_cache = json.load(f)
        else:
            self.geocode_cache = {}

        # Load route cache
        if os.path.exists(self.route_cache_file):
            with open(self.route_cache_file, 'r') as f:
                self.route_cache = json.load(f)
        else:
            self.route_cache = {}

    def _save_caches(self):
        """Save both caches to files."""
        with open(self.geocode_cache_file, 'w') as f:
            json.dump(self.geocode_cache, f, indent=2)
        with open(self.route_cache_file, 'w') as f:
            json.dump(self.route_cache, f, indent=2)

    def _get_address_key(self, address):
        """Generate a unique key for an address."""
        if isinstance(address, dict) and 'lat' in address and 'lng' in address:
            return f"coord_{address['lat']}_{address['lng']}"
        return f"addr_{address}"

    def _get_route_key(self, origin, destination, departure_time):
        """Generate a unique key for a route."""
        origin_key = self._get_address_key(origin)
        dest_key = self._get_address_key(destination)
        time_key = departure_time.strftime("%Y-%m-%d_%H:%M") if departure_time else "no_time"
        return f"{origin_key}_{dest_key}_{time_key}"

    def get_geocode(self, address):
        """Get cached geocode result for an address."""
        key = self._get_address_key(address)
        return self.geocode_cache.get(key)

    def set_geocode(self, address, coordinates):
        """Cache geocode result for an address."""
        key = self._get_address_key(address)
        self.geocode_cache[key] = coordinates
        self._save_caches()

    def get_route(self, origin, destination, departure_time):
        """Get cached route result."""
        key = self._get_route_key(origin, destination, departure_time)
        route_info = self.route_cache.get(key)
        
        # If route exists but doesn't have bike info, return None to force recalculation
        if route_info and 'biking_distance' not in route_info:
            return None
            
        return route_info

    def set_route(self, origin, destination, departure_time, route_info):
        """Cache route result."""
        key = self._get_route_key(origin, destination, departure_time)
        self.route_cache[key] = route_info
        self._save_caches()

    def clear_route_cache(self):
        """Clear the route cache."""
        self.route_cache = {}
        self._save_caches() 