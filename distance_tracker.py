import os
import json
import argparse
import pandas as pd
import csv
from datetime import datetime, timedelta
import googlemaps
from dotenv import load_dotenv
from cache_manager import CacheManager
import urllib.parse

class DistanceTracker:
    def __init__(self, api_key):
        self.gmaps = googlemaps.Client(key=api_key)
        self.cache = CacheManager()
        
    def geocode_address(self, address):
        """Geocode an address or return coordinates if already in coordinate format."""
        if isinstance(address, dict) and 'lat' in address and 'lng' in address:
            return address

        # Check cache first
        cached_coords = self.cache.get_geocode(address)
        if cached_coords:
            return cached_coords

        try:
            result = self.gmaps.geocode(address)
            if result:
                location = result[0]['geometry']['location']
                coords = {'lat': location['lat'], 'lng': location['lng']}
                # Cache the result
                self.cache.set_geocode(address, coords)
                return coords
            return None
        except Exception as e:
            print(f"Error geocoding address {address}: {str(e)}")
            return None

    def get_plus_code(self, coordinates):
        """Convert coordinates to Plus Code."""
        if not coordinates or 'lat' not in coordinates or 'lng' not in coordinates:
            return None
        try:
            result = self.gmaps.geocode({
                'lat': coordinates['lat'],
                'lng': coordinates['lng']
            })
            if result and 'plus_code' in result[0]:
                return result[0]['plus_code']['global_code']
            return None
        except Exception as e:
            print(f"Error generating Plus Code: {str(e)}")
            return None

    def get_coordinates_from_plus_code(self, plus_code):
        """Convert Plus Code to coordinates."""
        try:
            result = self.gmaps.geocode(plus_code)
            if result:
                location = result[0]['geometry']['location']
                return {
                    'lat': location['lat'],
                    'lng': location['lng']
                }
            return None
        except Exception as e:
            print(f"Error decoding Plus Code: {str(e)}")
            return None

    def get_route_info(self, origin, destination, departure_time=None):
        """Get route information for both driving and transit."""
        # Check cache first
        cached_route = self.cache.get_route(origin, destination, departure_time)
        if cached_route:
            return cached_route

        # Handle Plus Codes
        if isinstance(origin, str) and '+' in origin:
            origin_coords = self.get_coordinates_from_plus_code(origin)
        else:
            origin_coords = self.geocode_address(origin)

        if isinstance(destination, str) and '+' in destination:
            dest_coords = self.get_coordinates_from_plus_code(destination)
        else:
            dest_coords = self.geocode_address(destination)
        
        if not origin_coords or not dest_coords:
            return None

        try:
            # Get driving directions
            driving_result = self.gmaps.directions(
                origin_coords,
                dest_coords,
                mode="driving",
                departure_time=departure_time
            )

            # Get transit directions
            transit_result = self.gmaps.directions(
                origin_coords,
                dest_coords,
                mode="transit",
                departure_time=departure_time,
                alternatives=True,  # Get all alternatives
                transit_mode=['bus', 'subway', 'train', 'tram', 'rail'],  # Specify all transit modes
                transit_routing_preference='fewer_transfers'  # Prioritize routes with fewer transfers
            )

            # Get biking directions
            biking_result = self.gmaps.directions(
                origin_coords,
                dest_coords,
                mode="bicycling",
                departure_time=departure_time
            )

            if not driving_result or not transit_result or not biking_result:
                return None

            driving_leg = driving_result[0]['legs'][0]
            
            # Find the fastest transit route, considering both duration and number of transfers
            def route_score(route):
                leg = route['legs'][0]
                # Convert duration to minutes for easier comparison
                duration_minutes = leg['duration']['value'] / 60
                # Count actual transfers (steps that are transit)
                transfers = sum(1 for step in leg['steps'] if step['travel_mode'] == 'TRANSIT')
                # Calculate walking time
                walking_time = sum(step['duration']['value'] for step in leg['steps'] if step['travel_mode'] == 'WALKING') / 60
                # Penalize routes with more transfers and longer walking times
                return duration_minutes + (transfers * 15) + (walking_time * 0.5)  # Increased transfer penalty
            
            # Sort routes by score and take the best one
            sorted_routes = sorted(transit_result, key=route_score)
            fastest_transit = sorted_routes[0]
            transit_leg = fastest_transit['legs'][0]
            
            biking_leg = biking_result[0]['legs'][0]

            # Generate Plus Codes for coordinates
            origin_plus_code = self.get_plus_code(origin_coords)
            dest_plus_code = self.get_plus_code(dest_coords)

            # Count actual transit transfers
            transit_transfers = sum(1 for step in transit_leg['steps'] if step['travel_mode'] == 'TRANSIT')

            route_info = {
                'driving_distance': driving_leg['distance']['text'],
                'driving_duration': driving_leg['duration']['text'],
                'transit_distance': transit_leg['distance']['text'],
                'transit_duration': transit_leg['duration']['text'],
                'transit_steps': transit_transfers,  # Now showing actual transit transfers
                'biking_distance': biking_leg['distance']['text'],
                'biking_duration': biking_leg['duration']['text'],
                'origin_coords': origin_coords,
                'destination_coords': dest_coords,
                'origin_plus_code': origin_plus_code,
                'destination_plus_code': dest_plus_code
            }

            # Cache the result
            self.cache.set_route(origin, destination, departure_time, route_info)
            return route_info

        except Exception as e:
            print(f"Error getting route info: {str(e)}")
            return None

    def get_google_maps_url(self, origin, destination, mode="driving"):
        """Generate a Google Maps URL for the route."""
        if isinstance(origin, dict) and 'lat' in origin and 'lng' in origin:
            origin_str = f"{origin['lat']},{origin['lng']}"
        elif isinstance(origin, str) and '+' in origin:
            origin_str = urllib.parse.quote(origin, safe='+')
        else:
            origin_str = urllib.parse.quote(str(origin))

        if isinstance(destination, dict) and 'lat' in destination and 'lng' in destination:
            dest_str = f"{destination['lat']},{destination['lng']}"
        elif isinstance(destination, str) and '+' in destination:
            dest_str = urllib.parse.quote(destination, safe='+')
        else:
            dest_str = urllib.parse.quote(str(destination))

        # Ensure the mode is properly encoded
        mode = urllib.parse.quote(mode)
        
        # Build the URL with proper encoding
        base_url = "https://www.google.com/maps/dir/"
        params = {
            'api': '1',
            'origin': origin_str,
            'destination': dest_str,
            'travelmode': mode
        }
        return f"{base_url}?{urllib.parse.urlencode(params)}"

def parse_arguments():
    parser = argparse.ArgumentParser(description='Calculate distances between locations')
    parser.add_argument('--pair-id', help='Specific pair ID to process (e.g., us_brazil_routes)')
    parser.add_argument('--output', default='distances.csv', help='Output filename')
    parser.add_argument('--departure-day', choices=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                      help='Day of week for departure time')
    parser.add_argument('--departure-time', help='Time to leave (HH:MM format)')
    parser.add_argument('--force', action='store_true', help='Force recalculation even if cached')
    return parser.parse_args()

def get_next_day_of_week(day_name):
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    today = datetime.now()
    days_ahead = days.index(day_name) - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)

def main():
    load_dotenv()
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print("Error: GOOGLE_MAPS_API_KEY not found in environment variables")
        return

    args = parse_arguments()
    tracker = DistanceTracker(api_key)

    # Clear cache if force flag is used
    if args.force:
        tracker.cache.clear_route_cache()

    # Load configuration
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Prepare departure time if specified
    departure_time = None
    if args.departure_day and args.departure_time:
        next_day = get_next_day_of_week(args.departure_day)
        departure_time = datetime.combine(next_day, datetime.strptime(args.departure_time, '%H:%M').time())

    # Process routes
    results = []
    
    # Filter pairs if specific pair ID is provided
    pairs = {k: v for k, v in config.items() if not args.pair_id or k == args.pair_id}
    
    for pair_id, pair in pairs.items():
        origins = pair['origins']
        destinations = pair['destinations']
        
        # Calculate routes for all origin-destination pairs
        for origin_idx, origin in enumerate(origins):
            for dest_idx, destination in enumerate(destinations):
                # Skip if not forcing recalculation and route is cached
                if not args.force and tracker.cache.get_route(origin['location'], destination['location'], departure_time):
                    print(f"Skipping cached route: {origin['name']} -> {destination['name']}")
                    continue

                route_info = tracker.get_route_info(origin['location'], destination['location'], departure_time)
                if route_info:
                    # Generate Google Maps URLs for both driving and transit
                    driving_url = tracker.get_google_maps_url(origin['location'], destination['location'], "driving")
                    transit_url = tracker.get_google_maps_url(origin['location'], destination['location'], "transit")
                    biking_url = tracker.get_google_maps_url(origin['location'], destination['location'], "bicycling")
                    
                    results.append({
                        'pair_id': pair_id,
                        'origin_index': origin_idx,
                        'destination_index': dest_idx,
                        'origin_name': origin['name'],
                        'destination_name': destination['name'],
                        'origin_address': origin['location'],
                        'destination_address': destination['location'],
                        'origin_url': origin.get('url', ''),
                        'destination_url': destination.get('url', ''),
                        'origin_plus_code': route_info['origin_plus_code'],
                        'destination_plus_code': route_info['destination_plus_code'],
                        'driving_distance': route_info['driving_distance'],
                        'driving_duration': route_info['driving_duration'],
                        'driving_url': driving_url,
                        'transit_distance': route_info['transit_distance'],
                        'transit_duration': route_info['transit_duration'],
                        'transit_hops': route_info['transit_steps'],
                        'transit_url': transit_url,
                        'biking_distance': route_info['biking_distance'],
                        'biking_duration': route_info['biking_duration'],
                        'biking_url': biking_url
                    })

    # Create or append to CSV
    if results:
        df = pd.DataFrame(results)
        
        # Configure pandas display options for proper CSV formatting
        csv_options = {
            'index': False,
            'quoting': 1,  # csv.QUOTE_ALL - Quote all fields
            'escapechar': '\\',  # Use backslash as escape character
            'encoding': 'utf-8'
        }
        
        if os.path.exists(args.output):
            # Read existing headers to ensure consistency
            existing_df = pd.read_csv(args.output, nrows=0)
            if list(existing_df.columns) == list(df.columns):
                df.to_csv(args.output, mode='a', header=False, **csv_options)
            else:
                # If headers don't match, create a new file
                df.to_csv(args.output, **csv_options)
        else:
            df.to_csv(args.output, **csv_options)
            
        print(f"Added {len(results)} new routes to {args.output}")
    else:
        print("No new routes to process")

if __name__ == "__main__":
    main() 