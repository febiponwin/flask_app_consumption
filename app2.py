from flask import Flask, render_template, send_file
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import qrcode
import threading
import time
from io import BytesIO

# Flask app setup
app = Flask(__name__)
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
qr_code_expiry_time = None

def clear_qr_code():
    """Clears the QR code message after the specified duration."""
    global current_message, qr_code_expiry_time
    time.sleep(QR_DISPLAY_DURATION)
    with message_lock:
        current_message = None
        qr_code_expiry_time = None

def on_message(client, userdata, message):
    """Callback function for MQTT messages."""
    global current_message, qr_code_expiry_time
    payload = message.payload.decode("utf-8")
    print(f"Message received: {payload}")

    with message_lock:
        current_message = payload
        qr_code_expiry_time = time.time() + QR_DISPLAY_DURATION

    # Start a timer to clear the QR code
    threading.Thread(target=clear_qr_code, daemon=True).start()

mqtt_client.connect()
mqtt_client.subscribe(TOPIC, 1, on_message)

@app.route("/")
def index():
    """Main route to display the QR code."""
    with message_lock:
        qr_available = current_message is not None
    return render_template("index.html", qr_available=qr_available)

@app.route("/qr_code")
def get_qr_code():
    """Serve the QR code image dynamically."""
    with message_lock:
        if current_message:
            qr = qrcode.make(current_message)
            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            buffer.seek(0)
            return send_file(buffer, mimetype="image/png")
    return "", 404

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
