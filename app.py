import os

from flask_cors import CORS

from main_project import create_app


app = create_app()

# Allow frontends hosted elsewhere to call the API.
# Configure allowed origins via CORS_ORIGINS="http://localhost:3000,https://your-domain".
origins = os.getenv("CORS_ORIGINS", "*")
origins_list = [o.strip() for o in origins.split(",")] if origins != "*" else "*"
CORS(app, resources={r"/api/*": {"origins": origins_list}})


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    # debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    # app.run(host=host, port=port, debug=debug)
    app.run(host=host, port=port)

