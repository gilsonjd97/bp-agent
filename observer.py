from flask import Flask, jsonify, request
import requests
import uuid
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
import base64

app = Flask(__name__)

# Global variables to store MSK Key and sent UUID
msk_key_global = None
sent_uuid = None
msk_encoded = None

class FileObserver(FileSystemEventHandler):
    def __init__(self, filename, callback):
        self.filename = filename
        self.callback = callback

    def on_modified(self, event):
        if event.src_path == self.filename:
            self.callback()

def file_modified():
    print("File has been modified, processing...")
    try:
        with open('/home/contiki/coap-eap-controller/src/data.txt', 'r') as file:
            data = file.readlines()
    except FileNotFoundError:
        print("File not found")
        return
    except Exception as e:
        print("Error reading file: ", e)
        return

    data_dict = {}
    for line in data:
        key, value = line.strip().split(': ', 1)
        data_dict[key] = value

    global msk_key_global, sent_uuid
    msk_key_global = data_dict.get('MSK Key', '')  # Save MSK Key for later
    sent_uuid = str(uuid.uuid4())  # Generate and store UUID

    url = "http://example.com/api"  # Replace with the actual URL
    headers = {'Content-Type': 'application/json'}
    payload = {
        'uuid': sent_uuid,  # Send stored UUID
        'device': data_dict.get('Device', ''),
        'ip_address': data_dict.get('IP Address', ''),
        'mud-url': "http://example.com/mud.json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json() if response.headers.get('Content-Type') == 'application/json' else response.text
        print("POST request successful: ", response_data)
    except requests.RequestException as e:
        print("Error in POST request: ", e)

@app.route('/ack', methods=['POST'])
def ack_post():
    # Read the request data
    request_data = request.data
    
    # Attempt to parse the JSON data
    try:
        data = json.loads(request_data)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON"}), 400
  
    received_uuid = data.get("device_id", "")
    received_ack = data.get("ACK", "")

    if received_uuid != sent_uuid:
        return jsonify({"error": "UUID mismatch"}), 400
    if received_ack != 'ok':
        return jsonify({"error": "Invalid response value"}), 400

    # Your successful processing logic
    return jsonify({"message": "Success"}), 200

def send_msk():
    binary_data = bytes.fromhex(msk_key_global)
    
    global msk_encoded
    msk_encoded = base64.b64encode(binary_data).decode()
    
    url = "http://example.com/endpoint"  # Replace with the actual URL
    headers = {'Content-Type': 'application/json'}
    payload = {
        'device_id': sent_uuid,
        'base64Psk': msk_encoded
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json() if response.headers.get('Content-Type') == 'application/json' else response.text
        return jsonify({'status': 'Second POST request successful', 'response': response_data}), response.status_code
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/confirm', methods=['POST'])
def confirm_post():
    request_data = request.data
    
    try:
        data = json.loads(request_data)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON"}), 400
  
    received_uuid = data.get("device_id", "")
    received_ack = data.get("ACK", "")

    if received_uuid != sent_uuid:
        return jsonify({"error": "UUID mismatch"}), 400
    if received_ack != 'ok':
        return jsonify({"error": "Invalid response value"}), 400

    with open('/home/contiki/coap-eap-controller/src/ack.txt', 'w') as file:
        file.write("device_id: {},\nACK: {},\nMSK: {}".format(received_uuid, received_ack, msk_encoded))

    return jsonify({"message": "Success"}), 200

def start_observer():
    path = '/home/contiki/coap-eap-controller/src/data.txt'
    event_handler = FileObserver(path, file_modified)
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, use_reloader=False)).start()
    start_observer()
