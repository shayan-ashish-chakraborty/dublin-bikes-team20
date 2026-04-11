from flask import Flask

  
from .config import Config
from .station.bikes_original import bikes_bp
from .weather.routes import weather_bp
from .auth.auth import auth_bp
from .home.home import home_bp
from .chat.chat import chat_bp
from .journey.routes import journey_bp
from .station.routes import stations_bp
from .bike_forecast.routes import forecast_bp
import os

def create_app() -> Flask:
    app = Flask(__name__, static_folder='../main_project/static', template_folder='../main_project/templates')
    app.config.from_object(Config())

    # Set secret key for sessions and flash messages
    app.secret_key = os.getenv("SECRET_KEY", "devsecret")  # replace in production

    app.register_blueprint(weather_bp, url_prefix="/api/weather")
    app.register_blueprint(bikes_bp, url_prefix="/api/bikes")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
    app.register_blueprint(journey_bp, url_prefix="/journey")
    app.register_blueprint(stations_bp)
    app.register_blueprint(home_bp)

    # April 8 add machine learning models
    app.register_blueprint(forecast_bp, url_prefix="/forecast" )
    return app

