import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _load_dotenv_if_present() -> None:
    """Load environment variables from a .env or var.env file if one exists.

    Checks for `.env` first (recommended), then falls back to the legacy
    `var.env` name used in this repo. Has no effect if neither file is found.
    """
    # Support both .env (recommended) and legacy var.env used in this repo.
    if os.path.exists(".env"):
        load_dotenv(dotenv_path=".env")
    elif os.path.exists("var.env"):
        load_dotenv(dotenv_path="var.env")


# Load env file(s) before reading values into Config.
_load_dotenv_if_present()


@dataclass(frozen=True)
class Config:
    """Immutable application configuration loaded from environment variables.

    All values are read at import time via ``os.getenv``. Sensitive credentials
    (API keys, DB password) default to ``None`` or an empty string so the app
    can start without them in development, but will fail at runtime if a
    protected endpoint is called without the relevant key set.

    Attributes:
        FLASK_ENV: Runtime environment (``"production"`` or ``"development"``).
        CITY: Default city passed to OpenWeatherMap queries.
        OPENWEATHER_API_KEY: OpenWeatherMap API credential.
        JCDECAUX_API_KEY: JCDecaux Bikes API credential.
        JCDECAUX_CONTRACT: JCDecaux contract name (always ``"dublin"``).
        JCDECAUX_BASE_URL: Base URL for the JCDecaux VLS v1 API.
        GOOGLE_MAPS_API_KEY: Google Maps Platform credential (Geocoding + Directions).
        CURRENT_WEATHER_URI: OpenWeatherMap current-conditions endpoint URL.
        FORECAST_WEATHER_URI: OpenWeatherMap 3-hour forecast endpoint URL.
        STATIONS_URI: JCDecaux stations list endpoint URL.
        GEMINI_API_KEY: Google Gemini API credential (inactive chatbot backend).
        GROQ_API_KEY: Groq API credential (active chatbot backend).
        DB_HOST: MySQL host address.
        DB_PORT: MySQL port (string, default ``"3306"``).
        DB_USER: MySQL username.
        DB_PASSWORD: MySQL password.
        DB_NAME_WEATHER: Name of the OpenWeatherMap MySQL database.
        DB_NAME_JCDECAUX: Name of the JCDecaux MySQL database.
    """

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

    # AI chatbot 
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME_WEATHER: str = os.getenv("DB_NAME_WEATHER", "local_databaseopenweather")
    DB_NAME_JCDECAUX: str = os.getenv("DB_NAME_JCDECAUX", "local_databasejcdecaux")

