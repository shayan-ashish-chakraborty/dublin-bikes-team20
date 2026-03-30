from flask import Flask

from .config import Config
from .routes.bikes import bikes_bp
from .routes.weather import weather_bp
from .routes.auth import auth_bp #imported the auth page 
import os

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())

    # Set secret key for sessions and flash messages
    app.secret_key = os.getenv("SECRET_KEY", "devsecret")  # replace in production

    app.register_blueprint(weather_bp, url_prefix="/api/weather")
    app.register_blueprint(bikes_bp, url_prefix="/api/bikes")
    app.register_blueprint(auth_bp, url_prefix="/auth") #auth blueprint within create app function

    @app.get("/")
    def index():
        return {
            "service": "dublin-bikes-team20-backend",
            "endpoints": {
                "weather": "/api/weather",
                "bikes": "/api/bikes",
            },
        }

    return app

