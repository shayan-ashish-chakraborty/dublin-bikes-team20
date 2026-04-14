from flask import Blueprint, current_app, jsonify, request
import os
import requests
import logging
import time
from ..config import Config


chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)


def call_gemini_with_retry(endpoint, payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(endpoint, json=payload, timeout=(5, 25))
        except requests.exceptions.ConnectTimeout:
            logger.warning(f"Connection timeout (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
        if response.status_code == 200:
            return response
        elif response.status_code == 503:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"503 received, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                return response
        elif response.status_code == 429:
            if attempt < max_retries - 1:
                retry_after = response.headers.get("Retry-After")
                wait = int(retry_after) if retry_after else (5 * (attempt + 1))  # 5s, 10s, 15s
                logger.warning(f"429 rate limit, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                return response
        else:
            return response
    return response


@chat_bp.post("")
def chat():
    """Chat endpoint - calls Gemini API """
    try:
        data = request.get_json(silent=True)
        if not data or not data.get("messages"):
            return jsonify({"error": "Invalid request"}), 400

        messages = data.get("messages", [])
        system_instruction = data.get("systemInstruction", "")
        gemini_api_key = Config.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")

        if not gemini_api_key:
            return jsonify({"error": "API key not configured"}), 500

        # Build contents for Gemini API
        contents = [
            {
                "role": "user" if msg.get("role") == "user" else "model",
                "parts": [{"text": msg.get("content", "")}],
            }
            for msg in messages
            if msg.get("content")
        ]

        if not contents:
            return jsonify({"error": "No valid messages"}), 400

        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 400, "temperature": 1.0},
        }

        # gemini-2.0-flash: stable release, higher free-tier reliability than 2.5-flash
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"
        response = call_gemini_with_retry(endpoint, payload)

        if response.status_code == 200:
            result = response.json()
            reply = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return jsonify({"reply": reply})

        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            detail = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
            message = detail.get("error", {}).get("message") if isinstance(detail, dict) else None
            resp_payload = {
                "error": "API quota exceeded",
                "message": message or "Too many requests; you are being rate-limited by Gemini.",
            }
            if retry_after:
                resp_payload["retry_after_seconds"] = int(retry_after)
            return jsonify(resp_payload), 429

        else:
            logger.error(f"Gemini API error {response.status_code}: {response.text[:200]}")
            return jsonify({"error": "Service temporarily unavailable", "gemini_status": response.status_code}), 500

    except requests.RequestException as e:
        logger.error(f"Network error: {e}")
        return jsonify({"error": "Connection error"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500