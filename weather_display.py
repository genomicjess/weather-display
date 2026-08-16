#!/usr/bin/python
import sys
import os
import requests
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
ICON_DIR = os.path.join(SCRIPT_DIR, 'weather_icons')

libdir = os.path.join(os.path.expanduser('~'), 'e-Paper/RaspberryPi_JetsonNano/python/lib')
sys.path.insert(0, libdir)

from waveshare_epd import epd7in3e
from PIL import Image, ImageDraw, ImageFont

# API key and location come from .env, not the repo, so this stays shareable
API_KEY = os.environ.get("OWM_API_KEY")
LAT = os.environ.get("OWM_LAT")
LON = os.environ.get("OWM_LON")
LOCATION_LABEL = os.environ.get("DISPLAY_LOCATION_LABEL", "")

if not API_KEY or not LAT or not LON:
    print("Error: OWM_API_KEY, OWM_LAT, and OWM_LON must be set (check .env)")
    sys.exit(1)

print("Fetching weather data...")
try:
    # Get current weather
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=imperial"
    response = requests.get(url, timeout=10)
    weather = response.json()

    # Get forecast for rain probability
    forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=imperial"
    forecast_response = requests.get(forecast_url, timeout=10)
    forecast = forecast_response.json()

    # Get weather alerts
    alerts_url = f"https://api.openweathermap.org/data/3.0/onecall?lat={LAT}&lon={LON}&appid={API_KEY}&units=imperial"
    alerts_response = requests.get(alerts_url, timeout=10)
    alerts_data = alerts_response.json()
    alerts = alerts_data.get('alerts', [])

    # Extract data
    feels_like = int(weather['main']['feels_like'])
    wind_speed = int(round(weather.get('wind', {}).get('speed', 0)))
    description = weather['weather'][0]['description'].title()
    weather_icon = weather['weather'][0]['icon']

    # Today's real high/low come from the daily forecast, not the current
    # conditions endpoint (whose temp_min/temp_max is just the momentary
    # spread across nearby stations, not a day forecast).
    daily_data = alerts_data.get('daily', [])
    if daily_data:
        temp_min = int(daily_data[0]['temp']['min'])
        temp_max = int(daily_data[0]['temp']['max'])
    else:
        temp_min = int(weather['main']['temp_min'])
        temp_max = int(weather['main']['temp_max'])

    # Get rain probability for the whole day (not just the next 3-hour
    # block, which is all the /forecast endpoint's first entry covers)
    if daily_data:
        rain_prob = int(daily_data[0].get('pop', 0) * 100)
    elif 'list' in forecast and len(forecast['list']) > 0 and 'pop' in forecast['list'][0]:
        rain_prob = int(forecast['list'][0]['pop'] * 100)
    else:
        rain_prob = 0

    print(f"Feels like: {feels_like}°F (High: {temp_max}° Low: {temp_min}°)")
    print(f"Wind: {wind_speed} mph")
    print(f"Condition: {description}")
    print(f"Rain probability: {rain_prob}%")
    print(f"Active alerts: {len(alerts)}")

except Exception as e:
    print(f"Error fetching weather: {e}")
    sys.exit(1)

print("Waiting for display to be ready...")
time.sleep(3)

print("Initializing display...")
epd = epd7in3e.EPD()
epd.init()
epd.Clear()

try:
    print("Creating weather display...")
    image = Image.new('RGB', (800, 480), 'white')
    draw = ImageDraw.Draw(image)

    # Color palette: each color means one thing, consistently
    COLOR_PRIMARY = '#1565C0'  # brand blue: title, high/low, cool-weather advice
    COLOR_ALERT = '#D32F2F'    # weather alerts only
    COLOR_WARM = '#F57C00'     # warm-weather advice (shorts)
    COLOR_DARK = '#212121'     # main content: huge number, condition
    COLOR_GRAY = '#616161'     # secondary/meta text

    # Load fonts (Quicksand - rounder and friendlier than a system default)
    try:
        quicksand_bold = '/usr/share/fonts/truetype/quicksand/Quicksand-Bold.ttf'
        quicksand_medium = '/usr/share/fonts/truetype/quicksand/Quicksand-Medium.ttf'
        quicksand_regular = '/usr/share/fonts/truetype/quicksand/Quicksand-Regular.ttf'
        font_title = ImageFont.truetype(quicksand_bold, 60)
        font_alert = ImageFont.truetype(quicksand_bold, 26)
        font_huge = ImageFont.truetype(quicksand_bold, 100)
        font_large = ImageFont.truetype(quicksand_bold, 34)
        font_medium = ImageFont.truetype(quicksand_medium, 24)
        font_small = ImageFont.truetype(quicksand_regular, 20)
        font_advisory = ImageFont.truetype(quicksand_bold, 24)
    except:
        print("Using default font")
        font_title = font_huge = font_large = font_medium = font_small = font_advisory = font_alert = ImageFont.load_default()

    # Determine the condition icon and final description up front, so all
    # text below can be drawn once (no draw-then-clear-and-redraw needed)
    weather_id = weather['weather'][0]['id']
    visibility = int(weather.get('visibility', 10000))

    if visibility < 500:  # Dense fog
        icon_path = os.path.join(ICON_DIR, 'mist.png')
        description = 'Dense Fog'
    elif visibility < 2000:  # Haze/light fog
        icon_path = os.path.join(ICON_DIR, 'haze.png')
        description = 'Haze'
    elif 781 <= weather_id <= 781:  # Tornado!
        icon_path = os.path.join(ICON_DIR, 'tornado.png')
        description = 'Tornado'
    elif 300 <= weather_id <= 321:  # Drizzle
        icon_path = os.path.join(ICON_DIR, 'drizzle.png')
        description = 'Drizzle'
    elif 'thunder' in description.lower():
        icon_path = os.path.join(ICON_DIR, 'thunderstorm.png')
    elif 'rain' in description.lower():
        icon_path = os.path.join(ICON_DIR, 'rain.png')
    elif 'snow' in description.lower():
        icon_path = os.path.join(ICON_DIR, 'snow.png')
    elif weather_id == 800:  # Clear sky
        icon_path = os.path.join(ICON_DIR, 'clear.png')
    elif 801 <= weather_id <= 802:  # Few/scattered clouds (partly cloudy)
        icon_path = os.path.join(ICON_DIR, 'partly_cloudy.png')
        description = 'Partly Cloudy'
    else:  # Broken/overcast clouds
        icon_path = os.path.join(ICON_DIR, 'clouds.png')

    # Draw a small vacuum icon in front of Robin's name (his favorite thing)
    vacuum_img = Image.open(os.path.join(ICON_DIR, 'vacuum.png')).convert('RGBA')
    vacuum_img = vacuum_img.resize((75, 75))
    image.paste(vacuum_img, (12, 3), vacuum_img)

    # Draw Robin's name at top
    draw.text((100, 12), "ROBIN'S WEATHER", font=font_title, fill=COLOR_PRIMARY)

    # Everything on the right side shares one right-aligned edge, matching
    # the weather icon card's right edge rather than the canvas edge
    RIGHT_EDGE = 760

    def draw_right_aligned(text, y, font, fill, **kwargs):
        bbox = draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]
        draw.text((RIGHT_EDGE - width, y), text, font=font, fill=fill, **kwargs)

    # Backing behind the icon so pale icon elements (e.g. white/gray
    # clouds) stay visible against the white page instead of disappearing.
    # Top aligned with the visual top of the huge feels-like number below.
    draw.rounded_rectangle((590, 108, 760, 278), radius=20, fill='#A9D6F0')
    weather_img = Image.open(icon_path).convert('RGBA')
    weather_img = weather_img.resize((150, 150))
    image.paste(weather_img, (600, 118), weather_img)

    # Left column: laid out with a consistent gap between rows, measured
    # from each element's actual rendered height rather than guessed offsets
    GAP = 10
    LEFT_X = 50
    y_cursor = 80

    # Huge feels-like temperature, with a caption vertically centered beside it
    feels_like_text = f"{feels_like}°"
    draw.text((LEFT_X, y_cursor), feels_like_text, font=font_huge, fill=COLOR_DARK)
    number_bbox = draw.textbbox((LEFT_X, y_cursor), feels_like_text, font=font_huge)
    caption_bbox = draw.textbbox((0, 0), "Feels Like", font=font_medium)
    caption_height = caption_bbox[3] - caption_bbox[1]
    number_center_y = (number_bbox[1] + number_bbox[3]) // 2
    draw.text((number_bbox[2] + 15, number_center_y - caption_height // 2), "Feels Like", font=font_medium, fill=COLOR_GRAY)
    y_cursor = number_bbox[3] + GAP

    # High/Low
    high_low_text = f"High: {temp_max}°  Low: {temp_min}°"
    draw.text((LEFT_X, y_cursor), high_low_text, font=font_large, fill=COLOR_PRIMARY)
    bbox = draw.textbbox((LEFT_X, y_cursor), high_low_text, font=font_large)
    y_cursor = bbox[3] + GAP

    # Wind
    wind_text = f"Wind: {wind_speed} mph"
    draw.text((LEFT_X, y_cursor), wind_text, font=font_medium, fill=COLOR_GRAY)
    bbox = draw.textbbox((LEFT_X, y_cursor), wind_text, font=font_medium)
    y_cursor = bbox[3] + GAP

    # Condition
    draw.text((LEFT_X, y_cursor), description, font=font_large, fill=COLOR_DARK)
    bbox = draw.textbbox((LEFT_X, y_cursor), description, font=font_large)
    y_cursor = bbox[3] + GAP

    # WEATHER ALERTS - Robin loves tornados!
    if alerts:
        alert_event = alerts[0].get('event', 'Weather Alert')

        # Icon on the left, text wraps and right-aligns to RIGHT_EDGE.
        # Positioned below the weather icon card, not overlapping it.
        alert_icon_size = 70
        icon_x = 440
        icon_y = 295
        text_left = icon_x + alert_icon_size + 15
        max_alert_width = RIGHT_EDGE - text_left

        # Wrap alert text to multiple lines if needed
        words = f"ALERT: {alert_event}".split()
        lines = []
        current_line = []

        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font_alert)
            if bbox[2] - bbox[0] <= max_alert_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))

        # Load alert icon
        if 'tornado' in alert_event.lower():
            alert_img = Image.open(os.path.join(ICON_DIR, 'tornado.png')).convert('RGBA')
        else:
            alert_img = Image.open(os.path.join(ICON_DIR, 'warning.png')).convert('RGBA')
        alert_img = alert_img.resize((alert_icon_size, alert_icon_size))
        image.paste(alert_img, (icon_x, icon_y), alert_img)

        # Vertically center the text block against the icon
        line_bbox = draw.textbbox((0, 0), "Ag", font=font_alert)
        line_height = (line_bbox[3] - line_bbox[1]) + 6
        text_block_height = line_height * len(lines)
        text_start_y = icon_y + (alert_icon_size - text_block_height) // 2

        for i, line in enumerate(lines):
            draw_right_aligned(line, text_start_y + i * line_height, font_alert, COLOR_ALERT)

    # Clothing advice based on FEELS LIKE temperature (blue = cool, orange = warm)
    if feels_like < 45:
        coat_img = Image.open(os.path.join(ICON_DIR, 'winter_coat.png')).convert('RGBA')
        coat_img = coat_img.resize((56, 56))
        image.paste(coat_img, (LEFT_X, y_cursor), coat_img)
        draw.text((LEFT_X + 72, y_cursor + 14), "WEAR A COAT!", font=font_advisory, fill=COLOR_PRIMARY, stroke_width=1, stroke_fill=COLOR_PRIMARY)
        y_cursor += 56 + GAP

    elif feels_like < 60:
        jacket_img = Image.open(os.path.join(ICON_DIR, 'light_jacket.png')).convert('RGBA')
        jacket_img = jacket_img.resize((56, 56))
        image.paste(jacket_img, (LEFT_X, y_cursor), jacket_img)
        draw.text((LEFT_X + 72, y_cursor + 14), "WEAR A JACKET!", font=font_advisory, fill=COLOR_PRIMARY, stroke_width=1, stroke_fill=COLOR_PRIMARY)
        y_cursor += 56 + GAP

    elif feels_like > 75:
        shorts_img = Image.open(os.path.join(ICON_DIR, 'shorts.png')).convert('RGBA')
        shorts_img = shorts_img.resize((56, 56))
        image.paste(shorts_img, (LEFT_X, y_cursor), shorts_img)
        draw.text((LEFT_X + 72, y_cursor + 14), "SHORTS WEATHER!", font=font_advisory, fill=COLOR_WARM, stroke_width=1, stroke_fill=COLOR_WARM)
        y_cursor += 56 + GAP

    # Umbrella advice
    if rain_prob > 30:
        umbrella_img = Image.open(os.path.join(ICON_DIR, 'umbrella.png')).convert('RGBA')
        umbrella_img = umbrella_img.resize((56, 56))
        image.paste(umbrella_img, (LEFT_X, y_cursor), umbrella_img)
        draw.text((LEFT_X + 72, y_cursor + 14), f"TAKE UMBRELLA! ({rain_prob}%)", font=font_advisory, fill=COLOR_PRIMARY, stroke_width=1, stroke_fill=COLOR_PRIMARY)
        y_cursor += 56 + GAP

    # Location, date, and last-updated time, grouped together at the
    # bottom right, right-aligned with the weather icon card
    draw_right_aligned(LOCATION_LABEL, 400, font_small, COLOR_GRAY)
    date_text = datetime.now().strftime("%a, %b %d")
    draw_right_aligned(date_text, 426, font_small, COLOR_GRAY)
    now = datetime.now().strftime("%I:%M %p")
    draw_right_aligned(f"Updated: {now}", 452, font_small, COLOR_GRAY)

    print("Displaying...")
    epd.display(epd.getbuffer(image))

    print("Done!")
finally:
    epd.sleep()
