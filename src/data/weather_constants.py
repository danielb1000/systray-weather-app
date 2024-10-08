

beaufort_scale = [
    (1, "calm"),
    (6, "light air"),
    (12, "light breeze"),
    (20, "gentle breeze"),
    (29, "moderate breeze"),
    (39, "strong breeze"),
    (50, "near gale"),
    (61, "gale"),
    (74, "strong gale"),
    (float('inf'), "storm")
]

precipitation_scale = [
    (0, "no precipitation"),
    (2.5, "light rain"),
    (7.6, "moderate rain"),
    (25, "heavy rain"),
    (50, "very heavy rain"),
    (float('inf'), "extremely heavy rain")
]

weather_codes = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog and depositing rime fog",
    48: "Fog and depositing rime fog",
    51: "Drizzle: Light intensity",
    53: "Drizzle: Moderate intensity",
    55: "Drizzle: Dense intensity",
    56: "Freezing Drizzle: Light intensity",
    57: "Freezing Drizzle: Dense intensity",
    61: "Rain: Slight intensity",
    63: "Rain: Moderate intensity",
    65: "Rain: Heavy intensity",
    66: "Freezing Rain: Light intensity",
    67: "Freezing Rain: Heavy intensity",
    71: "Snow fall: Slight intensity",
    73: "Snow fall: Moderate intensity",
    75: "Snow fall: Heavy intensity",
    77: "Snow grains",
    80: "Rain showers: Slight intensity",
    81: "Rain showers: Moderate intensity",
    82: "Rain showers: Violent intensity",
    85: "Snow showers: Slight intensity",
    86: "Snow showers: Heavy intensity",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}

