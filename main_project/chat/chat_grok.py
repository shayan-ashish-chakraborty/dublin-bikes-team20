from flask import Blueprint, current_app, jsonify, request
import os
import requests
import logging
import time
from ..config import Config

chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)

# GROQ SETTINGS 
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = "llama-3.3-70b-versatile"   # free, fast

# BASE SYSTEM PROMPT 
BASE_SYSTEM = (
    "You are a helpful assistant for Dublin Bikes. "
    "Help users find stations, plan cycling routes, check weather, and give tips. "
    "Keep replies short and friendly."
    "When answering about bike availability, use ONLY the live station data "
    "provided below — never guess or make up numbers.\n\n"
)


def fetch_station_context(base_url: str) -> str:
    """Fetch a live station summary to inject into the chatbot system prompt.

    Calls the internal ``/api/stations`` endpoint and formats up to 50 stations
    as a compact plain-text block. Falls back to an empty string on any error
    so the chat endpoint continues to work without station context.

    Args:
        base_url: The application's base URL (e.g. ``"http://127.0.0.1:8000"``).

    Returns:
        A plain-text summary string listing station names, available bikes,
        available spaces, and status. Returns an empty string if the endpoint
        is unreachable or returns no data.
    """
    try:
        res = requests.get(f"{base_url}/api/stations", timeout=5)
        if res.status_code != 200:
            return ""
        stations = res.json()

        # Support both {"stations": [...]} and a bare list
        if isinstance(stations, dict):
            stations = stations.get("stations") or stations.get("data") or []

        if not stations:
            return ""

        lines = ["LIVE DUBLIN BIKES DATA (as of right now):"]
        for s in stations[:50]:  # cap at 50 stations to stay within token budget
            name      = s.get("name") or s.get("address") or "Unknown"
            available = s.get("available_bikes") or s.get("bikes") or s.get("availableBikes") or "?"
            spaces    = s.get("available_bike_stands") or s.get("spaces") or s.get("availableStands") or "?"
            status    = s.get("status", "OPEN")
            lines.append(f"- {name}: {available} bikes, {spaces} spaces ({status})")

        return "\n".join(lines) + "\n\n"

    except Exception as e:
        logger.warning(f"Could not fetch station context: {e}")
        return ""


def call_groq_with_retry(messages: list, api_key: str, max_retries: int = 3) -> requests.Response:
    """Send a chat completion request to the Grok API with retry logic.

    Retries on connection timeouts, 429 rate-limit responses (honouring
    ``Retry-After`` headers), and 503 service-unavailable responses using
    exponential back-off.

    Args:
        messages: List of OpenAI-format message dicts (``role`` + ``content``).
        api_key: Grok API key for the ``Authorization`` header.
        max_retries: Maximum number of attempts before giving up. Defaults to ``3``.

    Returns:
        The final ``requests.Response`` object (successful or not). The caller
        is responsible for checking ``response.status_code``.

    Raises:
        requests.exceptions.ConnectTimeout: If all retry attempts time out.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": 400,
        "temperature": 0.7,
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(GROQ_ENDPOINT, json=payload, headers=headers, timeout=(5, 25))
        except requests.exceptions.ConnectTimeout:
            logger.warning(f"Connection timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise

        if response.status_code == 200:
            return response
        elif response.status_code == 429:
            if attempt < max_retries - 1:
                retry_after = response.headers.get("Retry-After")
                wait = int(retry_after) if retry_after else (5 * (attempt + 1))
                logger.warning(f"429 rate limit, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                return response
        elif response.status_code == 503:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(f"503 received, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                return response
        else:
            return response

    return response


@chat_bp.post("")
def chat() -> tuple:
    """``POST /api/chat`` — Handle a chat completion request using the Grok LLM API.

    Injects live Dublin Bikes station data into the system prompt, then
    forwards the conversation history to Grok and returns the assistant reply.

    Uses:
        - :func:`fetch_station_context` — fetches live station data from ``GET /api/stations``
          and formats it as a plain-text block for the system prompt.
        - :func:`call_groq_with_retry` — sends the message list to the Grok API with
          automatic retry on rate-limit and service errors.

    Example request::

        POST /api/chat
        Content-Type: application/json

        {
            "messages": [
                {"role": "user", "content": "Which station has the most bikes right now?"}
            ]
        }

    Args:
        messages: List of OpenAI-format message dicts (JSON body, required).
            Each dict must have ``role`` (``"user"`` or ``"assistant"``) and ``content``.

    Returns:
        A Flask JSON response tuple. On success: ``{"reply": str}``, 200.
        On rate limit: ``{"error": ..., "message": ..., "retry_after_seconds": int}``, 429.
        On other errors: ``{"error": str}``, 400/500.
    """
    try:
        data = request.get_json(silent=True)
        if not data or not data.get("messages"):
            return jsonify({"error": "Invalid request"}), 400

        incoming_messages = data.get("messages", [])
        groq_api_key = getattr(Config, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")

        if not groq_api_key:
            return jsonify({"error": "GROQ_API_KEY not configured"}), 500

        # Build live station context and inject into system prompt
        base_url = request.host_url.rstrip("/")   # e.g. http://127.0.0.1:8000
        station_ctx = fetch_station_context(base_url)
        system_content = BASE_SYSTEM + station_ctx

        # Build OpenAI-format messages: system first, then conversation history
        messages = [{"role": "system", "content": system_content}]
        for msg in incoming_messages:
            role    = "user" if msg.get("role") == "user" else "assistant"
            content = msg.get("content", "").strip()
            if content:
                messages.append({"role": role, "content": content})

        if len(messages) <= 1:   # only system prompt, no user messages
            return jsonify({"error": "No valid messages"}), 400

        response = call_groq_with_retry(messages, groq_api_key)

        if response.status_code == 200:
            result = response.json()
            reply  = result["choices"][0]["message"]["content"]
            return jsonify({"reply": reply})

        elif response.status_code == 429:
            detail  = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
            message = detail.get("error", {}).get("message") if isinstance(detail, dict) else None
            resp_payload = {
                "error":   "API quota exceeded",
                "message": message or "Too many requests — Groq rate limit hit.",
            }
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                resp_payload["retry_after_seconds"] = int(retry_after)
            return jsonify(resp_payload), 429

        else:
            logger.error(f"Groq API error {response.status_code}: {response.text[:200]}")
            return jsonify({"error": "Service temporarily unavailable", "groq_status": response.status_code}), 500

    except requests.RequestException as e:
        logger.error(f"Network error: {e}")
        return jsonify({"error": "Connection error"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500