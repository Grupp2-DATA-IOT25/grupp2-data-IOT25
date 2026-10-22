
from flask import Flask, jsonify, send_from_directory
from pathlib import Path
import datetime
import urllib.request
import urllib.error

WEB_DIR = Path(__file__).resolve().parent.parent

app = Flask(
    __name__,
    static_folder=str(WEB_DIR / "static"),
    static_url_path="/static"
)


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


# Testdata för webbdesignen
@app.route("/api/test/servers/")
def servers():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({
        "server1": {
            "connected": True,
            "last_update": now,
            "Data": {
                "DeviceId": "amid-esp32",
                "Humidity": 23.7,
                "Temperature": 18.1
            }
        },
        "server2": {
            "connected": True,
            "last_update": now,
            "Data": {
                "DeviceId": "hassan-esp32",
                "Humidity": 18.4,
                "Temperature": 20.0
            }
        },
        "server3": {
            "connected": False,
            "last_update": None,
            "Data": {}
        }
    })


# Hämtar data från gruppens riktiga OPC UA API
@app.route("/api/servers")
def real_servers():
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:5000/api/servers",
            timeout=3
        ) as response:
            data = response.read()

        return app.response_class(
            data,
            content_type="application/json"
        )

    except (urllib.error.URLError, TimeoutError):
        return jsonify({
            "error": "Kunde inte nå OPC UA API"
        }), 503


if __name__ == "__main__":
    app.run(port=5001, debug=True)
