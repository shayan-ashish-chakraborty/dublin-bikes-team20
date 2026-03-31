from flask import Flask

  
from .config import Config
from .routes.bikes import bikes_bp
from .routes.weather import weather_bp
from .routes.auth import auth_bp
from .routes.home import home_bp  
import os

def create_app() -> Flask:
    app = Flask(__name__, static_folder='../sprint3_frontend_Leah/static', template_folder='../sprint3_frontend_Leah/templates')
    app.config.from_object(Config())

    # Set secret key for sessions and flash messages
    app.secret_key = os.getenv("SECRET_KEY", "devsecret")  # replace in production

    app.register_blueprint(weather_bp, url_prefix="/api/weather")
    app.register_blueprint(bikes_bp, url_prefix="/api/bikes")
    app.register_blueprint(auth_bp, url_prefix="/auth") 
    app.register_blueprint(home_bp)

    return app

