from flask import Blueprint, render_template
import pathlib


_TEMPLATES = "../../../main_project/templates"
_STATIC    = "../../../main_project/static"

home_bp = Blueprint(
    "frontend",
    __name__,
    template_folder=str(_TEMPLATES),
    static_folder=str(_STATIC),
    static_url_path="/static",
)



@home_bp.get("/")
def home():
    """
    GET /
    Home page — hero section, live weather strip, stats bar,
    and feature cards. See index.html for all the detail.
    """
    return render_template("index.html")


@home_bp.get("/weather")
def weather_page():
    return render_template("weather.html")