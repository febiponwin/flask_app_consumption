from flask import Flask, render_template, send_file
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import qrcode
import threading
import time
import os

# Flask app setup
app = Flask(__name__)
QR_CODE_PATH = "./static/qr_code.png"
QR_DISPLAY_DURATION = 30  # in seconds
TOPIC = "your-topic"

# AWS IoT Core Configuration
ENDPOINT = "your-aws-iot-endpoint.amazonaws.com"
CLIENT_ID = "FlaskMQTTClient"
CERT_DIR = "./certs/"
CA_PATH = CERT_DIR + "AmazonRootCA1.pem"
CERT_PATH = CERT_DIR + "device.pem.crt"
PRIVATE_KEY_PATH = CERT_DIR + "private.pem.key"

# MQTT Client setup
mqtt_client = AWSIoTMQTTClient(CLIENT_ID)
mqtt_client.configureEndpoint(ENDPOINT, 8883)
mqtt_client.configureCredentials(CA_PATH, PRIVATE_KEY_PATH, CERT_PATH)
mqtt_client.configureOfflinePublishQueueing(-1)
mqtt_client.configureDrainingFrequency(2)
mqtt_client.configureConnectDisconnectTimeout(10)
mqtt_client.configureMQTTOperationTimeout(5)

current_message = None
message_lock = threading.Lock()

def clear_qr_code():
    """Clears the QR code after the specified duration."""
    time.sleep(QR_DISPLAY_DURATION)
    with message_lock:
        if os.path.exists(QR_CODE_PATH):
            os.remove(QR_CODE_PATH)

def on_message(client, userdata, message):
    """Callback function for MQTT messages."""
    global current_message
    payload = message.payload.decode("utf-8")
    print(f"Message received: {payload}")

    with message_lock:
        current_message = payload
        qr = qrcode.make(payload)
        qr.save(QR_CODE_PATH)

    # Start a timer to clear the QR code
    threading.Thread(target=clear_qr_code, daemon=True).start()

mqtt_client.connect()
mqtt_client.subscribe(TOPIC, 1, on_message)

@app.route("/")
def index():
    """Main route to display the QR code."""
    with message_lock:
        qr_exists = os.path.exists(QR_CODE_PATH)
    return render_template("index.html", qr_exists=qr_exists)

@app.route("/qr_code")
def get_qr_code():
    """Serve the QR code image."""
    if os.path.exists(QR_CODE_PATH):
        return send_file(QR_CODE_PATH, mimetype="image/png")
    return "", 404

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
