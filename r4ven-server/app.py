from flask import Flask, render_template, jsonify
import json, os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "uploads", "location_log.json")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/locations")
def get_locations():
    entries = []

    with open(LOG_FILE, "r") as f:
        for line in f:
            print("RAW LINE:", line)  # Debug print
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entries.append(data)
            except json.JSONDecodeError as e:
                print("PARSE ERROR:", e)
                continue

    print("ENTRIES LOADED:", len(entries))  # ✅ confirm entries parsed
    return jsonify(entries)

if __name__ == "__main__":
    app.run(debug=True, port=5003)
