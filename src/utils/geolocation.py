from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

def get_city_from_coordinates(latitude: float, longitude: float)-> str:
    try:
        # Create a geolocator object using the Nominatim geocoder
        geolocator = Nominatim(user_agent="app")

        # Perform reverse geocoding with float coordinates
        location = geolocator.reverse((latitude, longitude), exactly_one=True)

        # Extract city, state, and country from location details
        if location:
            address = location.raw['address']
            city = address.get('city', '')
            town = address.get('town', '')
            village = address.get('village', '')
            hamlet = address.get('hamlet', '')
            suburb = address.get('suburb', '')
            municipality = address.get('municipality', '')
            state = address.get('state', '')  # This includes the state or administrative level
            country = address.get('country', '')

            # Get the first non-empty place name
            place_name = city or town or village or hamlet or suburb or municipality

            # Return place name with state and country, if available
            if place_name and state and country:
                return f"{place_name}, {state}, {country}"  # Format: "City, State, Country"
            elif place_name and country:
                return f"{place_name}, {country}"  # Format: "City, Country" if state isn't available
            elif place_name:
                return place_name  # If only place name is available
            else:
                return None

        else:
            print("Location not found")
            return "Not a legitimate location"

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error: {e}")
        return "GeocoderTimedOut or GeocoderServiecError happened"