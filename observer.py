import requests
import uuid
import json
import threading
import time
import base64
import os
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Global variables to store MSK Key and sent UUID
msk_key_global = None
uuid = None
msk_encoded = None

# HTTP request handler
class RequestHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/ack':
            self.handle_ack()
        elif self.path == '/confirm':
            self.handle_confirm()
        else:
            self.send_response(404)
            self.end_headers()

    def handle_ack(self):
        content_length = int(self.headers['Content-Length'])
        request_data = self.rfile.read(content_length)

        try:
            data = json.loads(request_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        received_uuid = data.get("uuid", "")
        received_ack = data.get("value", "")

        if received_uuid != uuid:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "UUID mismatch"}).encode())
            return

        print("Received ack, processing...")
        with open('/home/contiki/coap-eap-controller/src/ack.txt', 'w') as file:
            file.write("device_id: {},\nACK: {},\nMSK: {}".format(received_uuid, received_ack, msk_encoded))

        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"message": "Success"}).encode())

    def handle_confirm(self):
        content_length = int(self.headers['Content-Length'])
        request_data = self.rfile.read(content_length)

        try:
            data = json.loads(request_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return

        received_uuid = data.get("device_id", "")
        received_ack = data.get("ACK", "")

        if received_uuid != uuid:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "UUID mismatch"}).encode())
            return
        if received_ack != 'ok':
            self.send_response(400)
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid response value"}).encode())
            return

        with open('/home/contiki/coap-eap-controller/src/53.txt', 'w') as file:
            file.write("device_id: {},\nACK: {},\nMSK: {}".format(received_uuid, received_ack, msk_encoded))

        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"message": "Success"}).encode())

# Function to monitor file changes and send requests
def monitor_and_check():
    last_mtime_25 = None

    while True:
        # Check the 25.txt file
        try:
            mtime_25 = os.path.getmtime('/home/contiki/coap-eap-controller/src/25.txt')
            if mtime_25 != last_mtime_25:
                last_mtime_25 = mtime_25
                handle_25_file()
                # After handling 25.txt, wait for 20 seconds before checking 50.txt
                time.sleep(20)
                handle_50_file()
        except FileNotFoundError:
            print("File 25.txt not found")

        # Add a delay between checks
        time.sleep(1)

def handle_25_file():
    print("File 25.txt has been modified, processing...")
    try:
        with open('/home/contiki/coap-eap-controller/src/25.txt', 'r') as file:
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

    global msk_key_global, uuid
    msk_key_global = data_dict.get('msk', '')  # Save MSK Key for later
    uuid = data_dict.get('uuid', '')  # Save uuid for later

    url = "http://localhost:4321/boostrapping"  # Replace with the actual URL
    headers = {'Content-Type': 'application/json'}
    payload = {
        'uuid': uuid,  # Send stored UUID
        'device': data_dict.get('device', ''),
        'ip_address': data_dict.get('ip_address', ''),
        'mud-url': "http://localhost:8091/MUD_Collins_Bootstrapping"
    }

    try:
        response = retry_request(url, payload, headers)
        response_data = response.json() if response.headers.get('Content-Type') == 'application/json' else response.text
        print("POST request successful: ", response_data)
    except requests.RequestException as e:
        print("Error in POST request: ", e)

def handle_50_file():
    print("File 50.txt has been modified, processing...")
    file_path = '/home/contiki/coap-eap-controller/src/50.txt'

    try:
        with open(file_path, 'r') as file:
            data = file.readlines()
            if not data:
                print("File is empty")
                return
    except FileNotFoundError:
        print("File not found: {}".format(file_path))
        return
    except Exception as e:
        print("Error reading file {}: {}".format(file_path, e))
        return

    data_dict = {}
    for line in data:
        if ': ' in line:
            key, value = line.strip().split(': ', 1)
            data_dict[key] = value
        else:
            print("Line format incorrect: {}".format(line))
            continue

    if not msk_key_global:
        print("MSK Key not found")
        return

    try:
        binary_data = bytes.fromhex(msk_key_global)
        msk_encoded = base64.b64encode(binary_data).decode()
    except ValueError as e:
        print("Error encoding MSK Key: {}".format(e))
        return

    #Print the encoded MSK
    #print("msk_encoded = {}".format(msk_encoded))
    #print(msk_key_global)

    url = "http://localhost:5024/presentPsk"  # Replace with the actual URL
    headers = {'Content-Type': 'application/json'}
    payload = {
        'device_id': uuid,
        'base64Psk': msk_encoded
    }

    try:
        response = retry_request(url, payload, headers)
        response.raise_for_status()  # Raise an HTTPError on bad response
        response_data = response.json() if response.headers.get('Content-Type') == 'application/json' else response.text
        print({'status': 'Second POST request successful', 'response': response_data})

        # Write to 53.txt after successful POST response
        output_file_path = '/home/contiki/coap-eap-controller/src/53.txt'
        try:
            with open(output_file_path, 'w') as file:
                file.write("device_id: {},\nACK: {}".format(uuid, 'ok'))
        except Exception as e:
            print("Error writing to file {}: {}".format(output_file_path, e))
    except requests.RequestException as e:
        print({'error': str(e)})

def retry_request(url, payload, headers, retries=3, delay=5):
    for attempt in range(retries):
        try:
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            response.raise_for_status()  # Raise an HTTPError on bad response
            return response
        except requests.RequestException as e:
            print("Attempt {} failed: {}".format(attempt + 1, e))
            if attempt + 1 == retries:
                raise
            time.sleep(delay)

if __name__ == '__main__':
    # Start the HTTP server
    server_address = ('localhost', 8082)  # Use localhost or '10.0.0.8' as needed
    httpd = HTTPServer(server_address, RequestHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print("Serving at port", 8082)

    # Start file observer and checker
    monitor_and_check()
