from flask import Flask

from .config import Config
from .routes.bikes import bikes_bp
from .routes.weather import weather_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())

    app.register_blueprint(weather_bp, url_prefix="/api/weather")
    app.register_blueprint(bikes_bp, url_prefix="/api/bikes")

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

