import pandas as pd

# Process the hourly weather data into a dataframe
def process_hourly_weather(hourly, current_time_utc, params)-> pd.DataFrame:
    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        ),
        "temp": hourly.Variables(0).ValuesAsNumpy(),
        "humidity": hourly.Variables(4).ValuesAsNumpy(),
        "rain chance": hourly.Variables(1).ValuesAsNumpy(),
        "precipitation": hourly.Variables(2).ValuesAsNumpy(),
        "wind": hourly.Variables(3).ValuesAsNumpy(),
    }

    hourly_dataframe = pd.DataFrame(data=hourly_data)

    # Filter the DataFrame
    hourly_dataframe = hourly_dataframe[hourly_dataframe["date"] >= current_time_utc]  # axe rows previous to now
    hourly_dataframe = hourly_dataframe.head(25) # axe rows after 24hrs as theyre too far away

    # Convert date from utc to timezone of the checked location and also to a smaller format 
    hourly_dataframe['date'] = hourly_dataframe['date'].dt.tz_convert(params['timezone'])  
    hourly_dataframe['date'] = pd.to_datetime(hourly_dataframe['date']).apply(lambda x: x.strftime("%d/%m %Hh") if pd.notnull(x) else '')
    # 18.0 °C // 14km/h // 92% // 0.0mm
    hourly_dataframe['temp'] = hourly_dataframe['temp'].apply(lambda x: str(round(x, 1)) + "°C")
    hourly_dataframe['wind'] = hourly_dataframe['wind'].apply(lambda x: str(round(x)) + "km/h")
    hourly_dataframe['humidity'] = hourly_dataframe['humidity'].apply(lambda x: str(round(x)) + "%")
    hourly_dataframe['precipitation'] = hourly_dataframe['precipitation'].apply(lambda x: str(round(x, 1)) + "mm")
    # Rain will have more ! depending on how large the % to rain is
    hourly_dataframe['rain chance'] = hourly_dataframe['rain chance'].apply(lambda x: str(round(x)) + "% !" if round(x) > 0 else "0%").apply(lambda x: x + "!" if int(x.split("%")[0]) >= 25 else x).apply(lambda x: x + "!" if int(x.split("%")[0]) >= 50 else x).apply(lambda x: x + "!" if int(x.split("%")[0]) >= 75 else x).apply(lambda x: x + "!" if int(x.split("%")[0]) > 90 else x)
    
    return hourly_dataframe


def process_current_weather(current) -> dict:
    result = {
        'time': current.Time(),
        'temperature': current.Variables(0).Value(),
        'humidity': current.Variables(1).Value(),
        'apparent_temperature': current.Variables(2).Value(),
        'precipitation': current.Variables(3).Value(),
        'weather_code': current.Variables(4).Value(),
        'wind_speed': current.Variables(5).Value()
    }
    return result



def format_dataframe(df) -> str:
    # Define fixed widths for each column
    widths = {
        'date': 10,            # 10 characters for date
        'temp': 12,     # 12 characters for temperature
        'humidity': 9,         # 9 characters for humidity
        'rain chance': 13,     # 13 characters for rain chance
        'precipitation': 15,   # 15 characters for precipitation
        'wind': 8              # 8 characters for wind
    }

    formatted_rows = []
    
    # Header formatting - :< left adjusts based on char amount
    header = f"{'date':<{widths['date']}}  {'temperature':<{widths['temp']}}  {'rain chance':<{widths['rain chance']}}  {'humidity':<{widths['humidity']}}  {'precipitation':<{widths['precipitation']}}  {'wind':<{widths['wind']}}"
    formatted_rows.append(header)
    
    # Row formatting :< left adjusts based on char amount
    for index, row in df.iterrows():
        formatted_row = f"{row['date']:<{widths['date']}}  {row['temp']:<{widths['temp']}}  {row['rain chance']:<{widths['rain chance']}}  {row['humidity']:<{widths['humidity']}}  {row['precipitation']:<{widths['precipitation']}}  {row['wind']:<{widths['wind']}}"

        formatted_rows.append(formatted_row)
    
    return "\n".join(formatted_rows)