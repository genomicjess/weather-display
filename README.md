# Robin's Weather Display

Weather display for a Waveshare 7.3" e-ink screen (epd7in3e) on a Raspberry Pi,
built for my son Robin. Fetches current conditions, forecast, and alerts from
OpenWeatherMap and renders them to the panel, run on a cron schedule.

## Setup (fresh Pi)

1. Clone this repo, e.g. to `~/weather-display`.
2. Clone Waveshare's e-Paper library into `~/e-Paper` (kept separate since it's
   a large multi-board vendor repo, not part of this project):
   ```
   git clone https://github.com/waveshare/e-Paper.git ~/e-Paper
   ```
3. Install Python dependencies: `pip install -r requirements.txt` (or via apt,
   depending on how your Pi is set up).
4. Copy `.env.example` to `.env` and fill in your OpenWeatherMap API key:
   ```
   cp .env.example .env
   ```
5. Enable SPI on the Pi (`sudo raspi-config` -> Interface Options -> SPI).
6. Add a cron entry to run it on a schedule, e.g. every 30 minutes:
   ```
   */30 * * * * /home/robin/weather-display/update_weather.sh >> /home/robin/weather-display/weather.log 2>&1
   ```

## Files

- `weather_display.py` — fetches weather and draws it to the display.
- `update_weather.sh` — cron entry point; uses `flock` so overlapping runs
  skip instead of racing each other for the display's GPIO pins.
- `weather_icons/` — icon PNGs used for conditions/alerts/clothing advice.
- `.env` — holds `OWM_API_KEY` (not committed).

## Notes

- The OpenWeatherMap alerts endpoint (One Call 3.0) requires a paid API tier.
- The e-ink panel needs a few minutes to settle between refreshes; refreshing
  it back-to-back too quickly can cause the display init to hang waiting on
  the panel's BUSY pin.
