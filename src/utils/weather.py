from data.weather_constants import weather_codes

# Return the weather description based on the weather code
def get_weather_description(code) -> str:
    return weather_codes.get(code, "Unknown code")