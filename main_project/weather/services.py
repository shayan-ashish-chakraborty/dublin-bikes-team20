import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import text
from ..config import Config
from ..db import create_engine_for, DbConfig
from sqlalchemy.orm import sessionmaker

weather_db_cfg = DbConfig(
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    db_name=Config.DB_NAME_WEATHER
)
weather_engine = create_engine_for(weather_db_cfg)
WeatherSession = sessionmaker(bind=weather_engine)


def _fetch_nearest_weather(dt_str: str) -> dict | None:
    """
    DB-first, OpenWeather API fallback.
    Returns the nearest hourly weather record within ±3 h of dt_str, or None.
    dt_str must be "YYYY-MM-DD HH:MM:SS".
    """
    try:
        request_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None

    # 1. Try DB
    try:
        dt_low  = request_dt - timedelta(hours=3)
        dt_high = request_dt + timedelta(hours=3)
        db_session = WeatherSession()
        result = db_session.execute(
            text("""
                SELECT *,
                       ABS(TIMESTAMPDIFF(SECOND, future_dt, :dt)) AS diff
                FROM hourly
                WHERE future_dt BETWEEN :dt_low AND :dt_high
                ORDER BY diff ASC
                LIMIT 1
            """),
            {"dt": request_dt, "dt_low": dt_low, "dt_high": dt_high}
        )
        row = result.mappings().fetchone()
        db_session.close()
        if row:
            record = dict(row)
            record.pop("diff", None)
            return record
    except Exception:
        pass

    # 2. Fallback: OpenWeather API
    try:
        cfg = Config()
        r = requests.get(
            cfg.FORECAST_WEATHER_URI,
            params={"appid": cfg.OPENWEATHER_API_KEY, "q": cfg.CITY, "units": "metric"},
            timeout=10,
        )
        r.raise_for_status()
        raw = r.json()

        best_item, best_diff = None, None
        for item in raw.get("list", []):
            item_dt = datetime.strptime(item["dt_txt"], "%Y-%m-%d %H:%M:%S")
            diff = abs((item_dt - request_dt).total_seconds())
            if diff <= 10800 and (best_diff is None or diff < best_diff):
                best_item, best_diff = item, diff

        if best_item is None:
            return None

        now_str = datetime.now(tz=ZoneInfo("Europe/Dublin")).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "dt":         now_str,
            "future_dt":  best_item.get("dt_txt"),
            "feels_like": best_item["main"].get("feels_like"),
            "humidity":   best_item["main"].get("humidity"),
            "pop":        best_item.get("pop"),
            "pressure":   best_item["main"].get("pressure"),
            "temp":       best_item["main"].get("temp"),
            "weather_id": best_item["weather"][0]["id"] if best_item.get("weather") else None,
            "wind_speed": best_item.get("wind", {}).get("speed"),
            "wind_gust":  best_item.get("wind", {}).get("gust"),
            "rain_3h":    best_item.get("rain", {}).get("3h"),
            "snow_3h":    best_item.get("snow", {}).get("3h"),
        }
    except Exception:
        return None
