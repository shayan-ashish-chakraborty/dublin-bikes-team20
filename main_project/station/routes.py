from flask import Blueprint, jsonify, render_template, request

from main_project.station.services import (
    get_all_stations,
    format_station,
    station_predict_from_request,
)

stations_bp = Blueprint("stations", __name__)


@stations_bp.route("/api/stations")
def stations():
    """``GET /api/stations`` — Return live availability for all Dublin Bikes stations.

    Uses:
        - :func:`~main_project.station.services.get_all_stations` — fetches all stations from JCDecaux.
        - :func:`~main_project.station.services.format_station` — normalises each raw station dict.

    Returns:
        JSON list of formatted station dicts with live ``available_bikes``
        and ``available_stands``.
    """
    raw = get_all_stations()
    return jsonify([format_station(s) for s in raw])


@stations_bp.route("/api/stations/predict")
def stations_predict():
    """``GET /api/stations/predict`` — Run a multi-hour bike and dock prediction for one station.

    Uses:
        - :func:`~main_project.station.services.station_predict_from_request` — runs the full
          multi-hour ML pipeline and returns the forecast dict.

    Example request::

        GET /api/stations/predict?number=42&hours=8

    Args:
        number: JCDecaux station ID (query param, required).
        hours: Forecast horizon in hours, max 48. Defaults to 48 (query param).

    Returns:
        JSON prediction dict from
        :func:`~main_project.station.services.station_predict_from_request`,
        or an error JSON with status 400/503.
    """
    try:
        return jsonify(station_predict_from_request(request))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"prediction failed: {exc}"), 503


@stations_bp.route("/stations")
def stations_page():
    """``GET /stations`` — Render the stations map page.

    Returns:
        Rendered ``stations.html`` template. Live station data is fetched
        client-side from ``GET /api/stations``.
    """
    return render_template("stations.html")
