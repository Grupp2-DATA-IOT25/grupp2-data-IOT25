from flask import Flask, jsonify, send_from_directory
import datetime

app = Flask(__name__, static_folder="static")

@app.route("/")
def index():
    return send_from_directory(".", "index.html")
# Det här kan köras vid test!  kör annars app.route"api/servers/ GET (som finns i opcclient_web app.py)    
@app.route("api/test/servers/")
def servers():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return jsonify({
        "server1": {"connected": True, "last_update": now,
                    "Data": {"DeviceId": "amid-esp32", "Humidity": 23.7, "Temperature": 18.1}},
        "server2": {"connected": True, "last_update": now,
                    "Data": {"DeviceId": "hassan-esp32", "Humidity": 18.4, "Temperature": 20.0}},
        "server3": {"connected": False, "last_update": now, "Data": {}}
    })

if __name__ == "__main__":
    app.run(port=5000, debug=True)
