import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _load_dotenv_if_present() -> None:
    # Support both .env (recommended) and legacy var.env used in this repo.
    if os.path.exists(".env"):
        load_dotenv(dotenv_path=".env")
    elif os.path.exists("var.env"):
        load_dotenv(dotenv_path="var.env")


# Load env file(s) before reading values into Config.
_load_dotenv_if_present()


@dataclass(frozen=True)
class Config:

    # Flask
    FLASK_ENV: str = os.getenv("FLASK_ENV", "production")

    # External APIs
    CITY: str = os.getenv("CITY", "Dublin,IE")
    OPENWEATHER_API_KEY: str | None = os.getenv("OPENWEATHER_API_KEY")
    
    JCDECAUX_API_KEY: str | None = os.getenv("JCDECAUX_API_KEY")
    JCDECAUX_CONTRACT = "dublin"
    JCDECAUX_BASE_URL = "https://api.jcdecaux.com/vls/v1"
    
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
   
    CURRENT_WEATHER_URI: str = os.getenv(
        "CURRENT_WEATHER_URI", "https://api.openweathermap.org/data/2.5/weather"
    )
    FORECAST_WEATHER_URI: str = os.getenv(
        "FORECAST_WEATHER_URI", "https://api.openweathermap.org/data/2.5/forecast"
    )
    STATIONS_URI: str = os.getenv(
        "STATIONS_URI", "https://api.jcdecaux.com/vls/v1/stations"
    )

    # Gemini AI chatbot (create a key in Google AI Studio)
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME_WEATHER: str = os.getenv("DB_NAME_WEATHER", "local_databaseopenweather")
    DB_NAME_JCDECAUX: str = os.getenv("DB_NAME_JCDECAUX", "local_databasejcdecaux")

