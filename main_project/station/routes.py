from flask import Blueprint, jsonify, render_template, request

from main_project.station.services import (
    get_all_stations,
    format_station,
    station_predict_from_request,
)

stations_bp = Blueprint("stations", __name__)


@stations_bp.route("/api/stations")
def stations():
    raw = get_all_stations()
    return jsonify([format_station(s) for s in raw])


@stations_bp.route("/api/stations/predict")
def stations_predict():
    """Run a multi-hour bike and dock prediction for one station.

    Args:
        number: JCDecaux station ID (query param, required).
        hours: Forecast horizon in hours, max 48. Defaults to 48 (query param).

    Returns:
        JSON prediction dict from ``station_predict_from_request``, or an
        error JSON with status 400/503.
    """
    try:
        return jsonify(station_predict_from_request(request))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    except Exception as exc:
        return jsonify(error=f"prediction failed: {exc}"), 503


@stations_bp.route("/stations")
def stations_page():
    """Render the stations map page.

    Returns:
        Rendered ``stations.html`` template. Live station data is fetched
        client-side from ``GET /api/stations``.
    """
    return render_template("stations.html")
