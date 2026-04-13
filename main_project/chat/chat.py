from flask import Blueprint, current_app, jsonify, request
import os
import requests
import logging
from ..config import Config

chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)


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

        # Call Gemini API
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 400, "temperature": 1.0},
        }

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
        response = requests.post(endpoint, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            reply = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return jsonify({"reply": reply})
        
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            detail = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
            message = detail.get("error", {}).get("message") if isinstance(detail, dict) else None
            payload = {
                "error": "API quota exceeded",
                "message": message or "Too many requests; you are being rate-limited by Gemini.",
            }
            if retry_after:
                payload["retry_after_seconds"] = int(retry_after)

            return jsonify(payload), 429
        
        else:
            logger.error(f"Gemini API error {response.status_code}: {response.text[:200]}")
            return jsonify({"error": "Service temporarily unavailable", "gemini_status": response.status_code}), 500

    except requests.RequestException as e:
        logger.error(f"Network error: {e}")
        return jsonify({"error": "Connection error"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500
