import unittest
from unittest.mock import patch, MagicMock
import os

# ─────────────────────────────────────────────────────────
# HOW TO RUN:
#   python -m unittest test.py -v
#
#   With coverage:
#   coverage run -m unittest test.py
#   coverage report -m
#
# EXPECTED OUTPUT (if all tests pass):
#   test_TC1_format_returns_correct_values ... ok
#   test_TC2_missing_bike_fields_default_to_zero ... ok
#   test_TC3_detects_rain_from_rain_3h ... ok
#   test_TC4_detects_no_rain ... ok
#   test_TC5_parses_mocked_api_response ... ok
#   test_TC6_stations_page_loads_successfully ... ok
#   test_TC7_predict_without_number_returns_400 ... ok
#   Ran 7 tests in X.XXs — OK
# ─────────────────────────────────────────────────────────

# Set dummy environment variables BEFORE importing anything from main_project.
# When running tests locally, the .env file is not loaded automatically,
# so variables like DB_PORT are None. This causes a crash in auth.py when
# it tries to do int(None). These dummy values are safe stand-ins for testing
# and do NOT affect the real running app.

os.environ.setdefault("DB_PORT",     "3306")
os.environ.setdefault("DB_HOST",     "127.0.0.1")
os.environ.setdefault("DB_USER",     "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME_WEATHER",   "test_weather")
os.environ.setdefault("DB_NAME_JCDECAUX",  "test_jcdecaux")
os.environ.setdefault("JCDECAUX_API_KEY",  "test_key")
os.environ.setdefault("OPENWEATHER_API_KEY", "test_key")
os.environ.setdefault("SECRET_KEY", "test_secret")

# ══════════════════════════════════════════════════════════════════════
# SCENARIO 1 — Station Data Formatting
#
# WHAT WE ARE TESTING:
#   format_station() takes a raw response object from the JCDecaux API 
#   and converts it into a clean, consistent dictionary that the rest
#   of the app uses. This function is called every time the map loads,
#   so it is critical that it works correctly.
#
# TEST TYPE: Unit Test
#   We call the function directly with a known input and check the output.
#   No server, database, or internet connection is needed.
# ══════════════════════════════════════════════════════════════════════

class TestFormatStation(unittest.TestCase):

    def setUp(self):
        # This fake station object mimics the shape of a real JCDecaux API response.
        # setUp() runs before each test in this class, so both TC1 and TC2 can use it.
        self.raw_station = {
            "number": 42,
            "name": "Christchurch Place",
            "address": "Christchurch Place, Dublin 8",
            "position": {"lat": 53.3433, "lng": -6.2716},
            "status": "OPEN",
            "available_bikes": 5,
            "available_bike_stands": 10,
            "bike_stands": 15,
        }

    def test_TC1_format_returns_correct_values(self):
        """
        TC1 — Normal input: checks that format_station() maps all fields correctly.
        Input:    A full raw JCDecaux station object (number=42, bikes=5, stands=15)
        Expected: A clean dict with number=42, lat=53.3433, available_bikes=5,
                  available_stands=10, total_stands=15
        """
        from main_project.station.services import format_station
        result = format_station(self.raw_station)

        self.assertEqual(result["number"], 42)           # station ID is preserved
        self.assertEqual(result["lat"], 53.3433)         # latitude is extracted from nested dict
        self.assertEqual(result["available_bikes"], 5)   # available bikes mapped correctly
        self.assertEqual(result["available_stands"], 10) # available stands mapped correctly
        self.assertEqual(result["total_stands"], 15)     # total capacity mapped correctly

    def test_TC2_missing_bike_fields_default_to_zero(self):
        """
        TC2 — Edge case: checks that format_station() does NOT crash when
              bike availability fields are missing from the API response.
        Input:    A minimal station object with no bike/stand count fields
        Expected: available_bikes=0 and available_stands=0 (safe defaults, no crash)

        WHY THIS MATTERS:
          The real JCDecaux API sometimes omits availability fields for closed
          or inactive stations. Without this default, the app would throw a
          KeyError and the map page would fail to load entirely.
        """
        from main_project.station.services import format_station
        minimal_station = {
            "number": 1, "name": "Test", "address": "Addr",
            "position": {"lat": 53.0, "lng": -6.0}, "status": "CLOSED"
        }
        result = format_station(minimal_station)

        self.assertEqual(result["available_bikes"], 0)   # defaults to 0, not KeyError
        self.assertEqual(result["available_stands"], 0)  # defaults to 0, not KeyError


# ══════════════════════════════════════════════════════════════════════
# SCENARIO 2 — Rain Detection Logic
#
# WHAT WE ARE TESTING:
#   _infer_is_raining_from_row() reads a weather data row and decides
#   whether it is currently raining (returns 1) or not (returns 0).
#   This value is passed directly into the ML bike availability model
#   as a feature — if the rain detection is wrong, bike predictions
#   will also be wrong.
#
# TEST TYPE: Unit Test
#   Pure logic function — no external dependencies at all.
# ══════════════════════════════════════════════════════════════════════

class TestRainInference(unittest.TestCase):

    def test_TC3_detects_rain_from_rain_3h(self):
        """
        TC3 — Is raining: checks that rain is detected when rain_3h > 0.01.
        Input:    {"rain_3h": 0.5}  (above the 0.01 mm threshold)
        Expected: Returns 1  (meaning: yes, it is raining)
        """
        from main_project.station.services import _infer_is_raining_from_row
        result = _infer_is_raining_from_row({"rain_3h": 0.5})
        self.assertEqual(result, 1)  # 1 = raining

    def test_TC4_detects_no_rain(self):
        """
        TC4 — Not raining: checks that dry conditions are correctly identified.
        Input:    {"rain_3h": 0.0, "pop": 0.1}  (both below their thresholds)
        Expected: Returns 0  (meaning: no rain)
        """
        from main_project.station.services import _infer_is_raining_from_row
        result = _infer_is_raining_from_row({"rain_3h": 0.0, "pop": 0.1})
        self.assertEqual(result, 0)  # 0 = not raining


# ══════════════════════════════════════════════════════════════════════
# SCENARIO 3 — JCDecaux API Call (Mocked)
#
# WHAT WE ARE TESTING:
#   get_all_stations() calls the live JCDecaux API to fetch all Dublin
#   bike stations. We test that our code correctly handles the response.
#
# WHY WE USE MOCKING:
#   We cannot call the real JCDecaux API during tests because:
#     - It requires a real API key
#     - It has rate limits (too many calls = blocked)
#     - It returns live data that changes every minute (not repeatable)
#   Instead, we use @patch to replace requests.get with a fake function
#   that returns a response we define ourselves. This lets us test our
#   own parsing logic in a controlled, reliable way.
#
# TEST TYPE: Unit Test with Mocking
# ══════════════════════════════════════════════════════════════════════

class TestGetAllStationsMocked(unittest.TestCase):

    @patch("main_project.station.services.requests.get")
    # ↑ This line replaces requests.get with a fake (mock) version for this test only
    def test_TC5_parses_mocked_api_response(self, mock_get):
        """
        TC5 — Mocked API response: checks that get_all_stations() correctly
              handles and returns a list of stations from the API response.
        Input:    Mocked API response containing 1 station (number=1)
        Expected: Returns a Python list of length 1, with number=1
                  and confirms the API was called exactly once
        """
        # Define what our fake API response looks like
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()  # pretend no HTTP error occurred
        mock_response.json.return_value = [            # pretend this is what the API returned
            {
                "number": 1,
                "name": "St Stephen's Green",
                "position": {"lat": 53.33, "lng": -6.25},
                "status": "OPEN",
                "available_bikes": 3,
                "available_bike_stands": 12,
                "bike_stands": 15,
            }
        ]
        mock_get.return_value = mock_response  # when requests.get is called, return the above

        from main_project.station.services import get_all_stations
        result = get_all_stations()

        self.assertIsInstance(result, list)         # result should be a list
        self.assertEqual(len(result), 1)            # should contain exactly 1 station
        self.assertEqual(result[0]["number"], 1)    # station number should be 1
        mock_get.assert_called_once()               # confirm the API was "called" once


# ══════════════════════════════════════════════════════════════════════
# SCENARIO 4 — Flask Route Validation
#
# WHAT WE ARE TESTING:
#   That the web routes (URLs) in our Flask app respond correctly —
#   specifically that pages load (HTTP 200) and that bad/missing input
#   returns a proper error (HTTP 400) instead of crashing (HTTP 500).
#
# HOW IT WORKS:
#   Flask has a built-in test client that lets us simulate browser
#   requests (like typing a URL and pressing Enter) without needing
#   a real running server or database connection.
#
# TEST TYPE: Integration Test (Flask Test Client)
# ══════════════════════════════════════════════════════════════════════

class TestFlaskRoutes(unittest.TestCase):

    def setUp(self):
        # Create a test version of the Flask app before each test runs
        from app import app
        app.config["TESTING"] = True   # puts Flask in testing mode (better error messages)
        self.client = app.test_client() # simulates a browser making requests

    def test_TC6_stations_page_loads_successfully(self):
        """
        TC6 — Page load: checks that the /stations HTML page renders without error.
        Input:    GET request to /stations (like visiting the page in a browser)
        Expected: HTTP 200 (success — page loaded correctly)
        """
        response = self.client.get("/stations")
        self.assertEqual(response.status_code, 200)  # 200 = OK

    def test_TC7_predict_without_number_returns_400(self):
        """
        TC7 — Missing parameter: checks that the predict endpoint handles
              missing input gracefully instead of crashing.
        Input:    GET /api/stations/predict  (with no station number provided)
        Expected: HTTP 400 (Bad Request — tells the user what went wrong)
                  NOT HTTP 500 (which would mean the server crashed)

        WHY THIS MATTERS:
          Good input validation means users (and the frontend) get a helpful
          error message when they forget a required parameter, rather than
          seeing a generic server error.
        """
        response = self.client.get("/api/stations/predict")
        self.assertEqual(response.status_code, 400)  # 400 = Bad Request (expected)


# ─────────────────────────────────────────────────────────────────────
# This block runs the tests when you execute the file directly.
# verbosity=2 gives you a line per test showing ok/FAIL/ERROR.
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    unittest.main(verbosity=2)
