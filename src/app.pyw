import os
import json
import pprint
import datetime
import pytz
import threading
import customtkinter
import requests_cache
import openmeteo_requests
import pandas as pd
from tkintermapview import TkinterMapView

from PIL import Image, ImageDraw, ImageFont
from pystray import Icon, Menu, MenuItem
from retry_requests import retry
from timezonefinder import TimezoneFinder

from data.weather_constants import beaufort_scale, precipitation_scale

from utils.geolocation import get_city_from_coordinates
from utils.weather import get_weather_description
from utils.formatting import process_hourly_weather
from utils.formatting import process_current_weather
from utils.formatting import format_dataframe

from functools import partial

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Setup CustomTkinter appearance and theme
customtkinter.set_appearance_mode("System")  # Modes: system (default), light, dark
customtkinter.set_default_color_theme("dark-blue")  # Themes: blue (default), dark-blue, green

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after=60)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Object used to find timezone based on config coordinates /
tf = TimezoneFinder()

# Create a thread lock for synchronization
thread_lock = threading.Lock()

# move to utils pls
def config_load():
    default_config = {  
        "latitude": "0.0",
        "longitude": "0.0"
    }

    try:
        # Load config file
        with open('config.json') as config_file:
            config = json.load(config_file)

    except (FileNotFoundError, json.JSONDecodeError):
        # If the config file is missing or invalid, use the default config and recreate the file
        config = default_config
        print("Config file not found or invalid. Creating a new one with default values.")
        with open('config.json', 'w') as config_file:
            json.dump(default_config, config_file, indent=4)

    # Find timezone based on the config coords. will be used to pass to the datetime converters later on
    timezone = tf.timezone_at(lat=float(config["latitude"]), lng=float(config["longitude"]))

    return config, timezone


# move to utils

# Returns a PIL image object of a given number with the specified size (64x64 by default).
def create_number_icon(number: int, size=64):

    number = str(number)

    # Create a blank image with a transparent background (RGBA mode) and initialise ImageDraw on such image
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    font_size = int(size * 0.99)  # Adjust font size to be large
    try:
        font = ImageFont.truetype("consola.ttf", font_size)  # Consolas font
    except IOError:
        font = ImageFont.load_default(size = font_size)  # Fallback if font file is not available
    
    # Calculate the text bounding box to center the number
    text_bbox = draw.textbbox((0, 0), number, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    # Calculate position for centering the text in the image
    position = (
        (size - text_width) // 2 - text_bbox[0],  
        (size - text_height) // 2 - text_bbox[1]  
    )
    
    # Draw the number in white
    draw.text(position, number, fill='white', font=font)

    return img


get_data_count = 0 # Count how many times this function is called. for debug purposes
def getdata() -> tuple[dict, str]:
    global get_data_count
    get_data_count += 1

    # API request params & loading coordinates from config file
    # config is latitude and longitude
    global config, timezone
    config, timezone = config_load()

    global params  # Make sure params is accessible outside the function, button_function() will need it
    params = {
            "latitude": config["latitude"],
            "longitude": config["longitude"],
            "current": ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation", "weather_code", "wind_speed_10m"],
            "hourly": ["temperature_2m", "precipitation_probability", "precipitation", "wind_speed_10m", "relative_humidity_2m"],
            "timezone": timezone,
            "forecast_days": 2
    }

    try:
        url = "https://api.open-meteo.com/v1/forecast"
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]  # Single location response (can extend to loop for multiple locations)
        
        # Extract and return current AND hourly weather variables
        current =  response.Current()
        hourly = response.Hourly()

        # Process the "current" response to a dict
        result_current = process_current_weather(current)

        current_time = current.Time() # Get current time of the place we're looking up
        current_time_utc = pd.to_datetime(current_time, unit="s", utc=True) # Convert the time we get to utc
        hourly_dataframe = process_hourly_weather(hourly, current_time_utc, params) # process_hourly_weather returns dataframe with forecast from current_time_utc to 24hrs after
        hourly_dataframe_as_string = format_dataframe(hourly_dataframe) # Turn dataframe into a properly formatted left-adjusted pretty string

        # pprint.pprint(result_current)
        # print()
        # print(hourly_dataframe)
        # print()
        print(f"^^call #{get_data_count} for getdata()")

        return (result_current, hourly_dataframe_as_string)

    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return None, None



# Initialize the CustomTkinter app
app = customtkinter.CTk()
app.title("Weather App")
# app.geometry("600x400")  # Set a default size for the window
app.resizable(False, False)

# Frame that shows todays weather
frame_left = customtkinter.CTkFrame(master=app, fg_color=app.cget("fg_color"))
frame_left.grid(row=0, column=0, padx=20, pady=10, sticky="nsew") 

# Frame that shows future forecast 
frame_bottom = customtkinter.CTkFrame(master=app, fg_color="#222222")
frame_bottom.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")

# Frame that will hold refresh button etc
frame_right = customtkinter.CTkFrame(master=app, fg_color=app.cget("fg_color"))
frame_right.grid(row=0, column=1, padx=20, pady=10, sticky="nsew")  

# Allow frames to resize dynamically to fit their contents
frame_left.grid_propagate(True)
frame_right.grid_propagate(True)
frame_bottom.grid_propagate(True)

# StringVars for holding and updating weather data
last_refresh = customtkinter.StringVar(value="Last refresh: Never")
last_attempt = customtkinter.StringVar(value="Last attempt: Never")
precipitation = customtkinter.StringVar(value="N/A")
weather_code = customtkinter.StringVar(value="N/A")
actual_temp = customtkinter.StringVar(value="N/A")
humidity = customtkinter.StringVar(value="N/A")
rel_temp = customtkinter.StringVar(value="N/A")
wind = customtkinter.StringVar(value="N/A")

# StringVar to show in UI what location we're checking
lat_lon = customtkinter.StringVar(value="N/A")

# StringVars for forecast
forecast_text = customtkinter.StringVar(value="N/A")

# Refresh button behaviour
scheduled_call_id = None
def button_function():
    global scheduled_call_id

    # Define a worker function to fetch data in the background
    def worker():
        current, hourly_dataframe_as_string = getdata()

        global location_name
        location_name = get_city_from_coordinates(params['latitude'],params['longitude']) # This is a network function so we put it in the background thread instead of calling it later on

        # Update the UI on the main thread using app.after()
        app.after(0, update_ui, current, hourly_dataframe_as_string)

    # Run the worker
    threading.Thread(target=worker, daemon=True).start()

    # Cancel any previously scheduled call
    if scheduled_call_id is not None:
        app.after_cancel(scheduled_call_id)

    # Schedule the function to run again after 5 minutes (300000 ms), and keep track of the id of such call
    scheduled_call_id = app.after(300000, button_function)  # 300,000 milliseconds = 5 minutes

    def update_ui(current, hourly_dataframe_as_string):
        wind_beaufort = "N/A"  # Default value
        for speed, description in beaufort_scale:
            if current['wind_speed'] < speed:
                wind_beaufort = description
                break

        precipitation_description = "N/A"  # Default value
        for threshold, description in precipitation_scale:
            if current['precipitation'] <= threshold:
                precipitation_description = description
                break

        # Update StringVars with the current data
        precipitation.set(  f"{current['precipitation']:.2f} mm - {precipitation_description}")
        weather_code.set(   f"{get_weather_description(int(current['weather_code']))}")
        actual_temp.set(    f"{current['temperature']:.2f} °C")
        rel_temp.set(       f"{current['apparent_temperature']:.2f} °C - relative temp")
        humidity.set(       f"{current['humidity']:.2f}% humidity")
        wind.set(           f"{current['wind_speed']:.2f} km/h - {wind_beaufort}")

        # Update forecast StringVar
        forecast_text.set(hourly_dataframe_as_string)

        # Update last refresh time, attempt, and location
        last_refresh.set(
            f"Last refresh: {datetime.datetime.fromtimestamp(current['time'], pytz.utc) 
                            .astimezone(pytz.timezone(timezone))  
                            .strftime('%d-%m-%Y %H:%M:%S')}"
        )
        last_attempt.set(
            f"Last attempt: {datetime.datetime.now(pytz.timezone(timezone))
                            .strftime('%d-%m-%Y %H:%M:%S')}"
        )
        # Update coordinates string
        lat_lon.set(f"{float(params['latitude']):.4f}\n{float(params['longitude']):.4f}\n{location_name}") # [:7] so it only shows first 7 chars, aka turn 39.03242304293402 into 30.0324
        # lat_lon.set(lat_lon.get()+ "\n" + location_name)

        # change icon to the number of current temp
        # button_function is called by default when the app opens BEFORE icon is created so we have to handle/ignore this error
        try:
            icon.icon = create_number_icon(int(current["temperature"]))
        except NameError as e: 
            print(f"Error: {e},\t this is probably the first time button_function was called, which is before the app's icon is initialised. No issues")
            pass



# Button for refreshing the weather data
button = customtkinter.CTkButton(master=frame_right, font=("Consolas", 20, "bold"), text="Refresh", command=button_function)
button.grid(row=0, column=0, padx=20, pady=10)

# Create labels for the data in the left frame
variables = [actual_temp, humidity, weather_code, wind, precipitation]  # Including the weather code and wind, could also add rel_temp since we define a StringVar for it and we request it in the request (apparent_temperature)
for index, var in enumerate(variables):
    label_value = customtkinter.CTkLabel(master=frame_left, justify=customtkinter.LEFT, textvariable=var, font=("Consolas", 20, "bold"),)
    label_value.grid(row=index, column=0, padx=20, pady=5, sticky="w")  # Values aligned to the left

# Create labels for the last refresh and last attempt below the button
label_last_refresh = customtkinter.CTkLabel(master=frame_right, textvariable=last_refresh, font=("Consolas", 14, "bold"))
label_last_refresh.grid(row=1, column=0, padx=20, pady=0)
label_last_attempt = customtkinter.CTkLabel(master=frame_right, textvariable=last_attempt, font=("Consolas", 14, "bold"))
label_last_attempt.grid(row=2, column=0, padx=20, pady=0)
label_lat_lon = customtkinter.CTkLabel(master=frame_right, textvariable=lat_lon, font=("Consolas", 14, "bold"))
label_lat_lon.grid(row=3, column=0, padx=20, pady=5)

button2 = customtkinter.CTkButton(master=frame_right, font=("Consolas", 14, "bold"), text="change location", fg_color="#111111", hover_color="#333333" ,command=partial(print,"teste"))
button2.grid(row=4, column=0, padx=0, pady=0)

# Create labels for the hourly data
forecast_text_label = customtkinter.CTkLabel(master=frame_bottom, textvariable=str(forecast_text), font=("Consolas", 14, "bold"))
forecast_text_label.grid(row=0, column=0, padx=20, pady=5)

# Update geometry to ensure all widgets are packed and calculated
app.update()

# Get the screen dimensions
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

# Get the window dimensions
window_width = app.winfo_width()
window_height = app.winfo_height()

# Calculate the position for the window to be placed
x_position = int((screen_width / 2) - (window_width / 2))
y_position = int((screen_height / 4) - (window_height / 2))


# Replicate a button click when the app opens
button_function()


# Default icon tray image
def create_image():
    """Create a system tray icon image (a simple black and white square)."""
    width, height = 64, 64
    image = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width // 2, height // 2], fill="white")
    draw.rectangle([width // 2, height // 2, width, height], fill="white")
    return image

def on_quit(icon, item):
    """Quit the system tray app."""
    with thread_lock:
        icon.stop() 
        app.quit()

def show_window(icon=None, item=None):
    """Show the window when restored from system tray."""
    with thread_lock:
        app.after(0, app.deiconify)

def hide_window():
    """Hide the window and minimize to the system tray."""
    with thread_lock:
        app.withdraw()

# Override the close window (X) behavior
def minimize_to_tray():
    """Minimize the window to the system tray."""
    threading.Thread(target=hide_window).start()
app.protocol("WM_DELETE_WINDOW", minimize_to_tray)

# Create the systray icon instance and add menu to it
icon = Icon(
    name="Weather App",
    icon=create_image(),
    title="Weather app (mouse over icon text)")
icon.menu = Menu(
            MenuItem("Show", show_window, default=True),
            MenuItem("Quit", on_quit))


# Start the tray icon in a separate thread
def run_tray():
    icon.run()
(threading.Thread(target=run_tray, daemon=True)).start()









# this code is messy rn
# EXTREMELY LAGGY TO USE THESE FUNCTIONALITIES

def open_map_window():
    """Open a new window with a map for selecting a location."""

    # Create a new top-level window so it appears in front of everything
    map_window = customtkinter.CTkToplevel()
    map_window.geometry("1000x1000")
    map_window.title("Select a Location")
    # Bring the new window to the front and keep it focused
    map_window.lift()  # Bring the window to the front
    map_window.focus_force()  # Force focus on the new window
    map_window.attributes("-topmost", True)  # Keep on top for now
    map_window.after(500, lambda: map_window.attributes("-topmost", False))  # Then turn off always-on-top after 500ms

    # Create a map widget inside the new window
    map_widget = TkinterMapView(map_window, width=1000, height=1000, corner_radius=0)
    map_widget.pack(fill="both", expand=True)
    map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png", max_zoom=6)  # OpenStreetMap (default)
    
    # Center the map to the current coordinates from the config or a default location
    if config and "latitude" in config and "longitude" in config:
        map_widget.set_position(float(config["latitude"]), float(config["longitude"]))
    else:
        map_widget.set_position(0.0, 0.0)  # Center to a default lat/lon

    map_widget.set_zoom(6)  # Set initial zoom level

    def update_config(lat_lon_tuple):
        """Update the config.json file with new latitude and longitude values."""
        
        lat, lon = lat_lon_tuple  # Unpack the tuple into latitude and longitude

        # Load the existing config file if it exists, otherwise use an empty dictionary
        try:
            with open('config.json', 'r') as config_file:
                config_data = json.load(config_file)
        except FileNotFoundError:
            config_data = {}  # Create a new dictionary if file does not exist

        # Update latitude and longitude
        config_data["latitude"] = str(lat)
        config_data["longitude"] = str(lon)

        # Write the updated config data back to the config.json file
        with open('config.json', 'w') as config_file:
            json.dump(config_data, config_file, indent=4)

    map_widget.add_right_click_menu_command(label="Set location",
                                            command=update_config,
                                            pass_coords=True)

# Attach the open_map_window function to button2
button2.configure(command=open_map_window)


# Run the main loop for the Tkinter app
app.mainloop()




# TODO
# need to test how it works when offline