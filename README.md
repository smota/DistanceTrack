# Distance Tracker

A Python script that calculates distances and travel times between multiple locations using Google Maps API. The script supports both driving and transit directions, and includes caching to minimize API calls.

## Features

- Calculate distances and travel times for multiple origin-destination pairs
- Support for both driving and transit directions
- Caching system to minimize API calls
- Support for Google Plus Codes (Open Location Codes)
- Generate Google Maps URLs for easy route viewing
- Configurable departure times
- CSV output with detailed route information

## Setup

1. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project directory with your Google Maps API key:
   ```
   GOOGLE_MAPS_API_KEY=your_api_key_here
   ```

3. Configure your location pairs in `config.json`:
   ```json
   {
     "pair_id": {
       "origins": [
         "Address or Plus Code 1",
         "Address or Plus Code 2"
       ],
       "destinations": [
         "Address or Plus Code 1",
         "Address or Plus Code 2"
       ]
     }
   }
   ```

## Usage

Run the script with:
```bash
python distance_tracker.py
```

### Command Line Options

- `--pair-id`: Process a specific pair ID (e.g., `us_brazil_routes`)
- `--output`: Specify output filename (default: `distances.csv`)
- `--departure-day`: Day of week for departure time (e.g., `Monday`, `Tuesday`, etc.)
- `--departure-time`: Time to leave in HH:MM format (e.g., `09:00`)
- `--force`: Force recalculation even if cached

### Examples

Calculate routes for next Monday at 9 AM:
```bash
python distance_tracker.py --departure-day Monday --departure-time 09:00
```

Process a specific pair with forced recalculation:
```bash
python distance_tracker.py --pair-id us_brazil_routes --force
```

## Location Formats

The script supports three formats for locations:

1. **Address Strings**: Full addresses (e.g., "New York, NY")
2. **Coordinates**: Latitude/longitude pairs (e.g., `{"lat": 40.7128, "lng": -74.0060}`)
3. **Plus Codes**: Google's Open Location Codes (e.g., "87G8P27V+JG")

Plus Codes are particularly useful for:
- Locations without street addresses
- More precise location sharing
- Shorter, more shareable location references
- Offline location sharing

## Caching

The script implements two types of caching:

1. **Geocoding Cache**: Stores coordinates for addresses to prevent repeated geocoding
   - Saved in `.cache/geocode_cache.json`
   - Includes both address-to-coordinates and Plus Code-to-coordinates mappings

2. **Route Cache**: Stores route information for origin-destination pairs
   - Saved in `.cache/route_cache.json`
   - Includes departure time in the cache key
   - Caches both driving and transit routes

Use the `--force` flag to bypass the cache and recalculate routes.

## Output

The script generates a CSV file with the following columns:

- `pair_id`: Identifier for the origin-destination pair
- `origin_index`: Index of the origin in the origins list
- `destination_index`: Index of the destination in the destinations list
- `origin_address`: Full address or Plus Code of the origin
- `destination_address`: Full address or Plus Code of the destination
- `origin_plus_code`: Plus Code for the origin location
- `destination_plus_code`: Plus Code for the destination location
- `driving_distance`: Distance for driving route
- `driving_duration`: Duration for driving route
- `driving_url`: Google Maps URL for driving directions
- `transit_distance`: Distance for transit route
- `transit_duration`: Duration for transit route
- `transit_hops`: Number of transit steps/transfers
- `transit_url`: Google Maps URL for transit directions

The Google Maps URLs allow you to:
- View the route on the map
- Get turn-by-turn directions
- See alternative routes
- Check real-time traffic conditions

If the output file already exists, new results will be appended to it.

## API Usage

The script uses the Google Maps API for:
- Geocoding addresses to coordinates
- Calculating driving and transit routes
- Generating Plus Codes

Each API call counts towards your quota:
- Geocoding API: $5 per 1000 requests
- Directions API: $5 per 1000 requests

The caching system helps minimize API calls by storing results for repeated queries.

## Error Handling

The script includes error handling for:
- API failures
- Invalid addresses
- Invalid Plus Codes
- Network issues
- Cache misses

Errors are logged to the console, and the script continues processing other routes.

## Contributing

Feel free to submit issues and enhancement requests! 