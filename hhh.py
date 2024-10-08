import asyncio
import websockets
import json
from datetime import datetime
import tkinter as tk
from tkinter import ttk
from fastapi import FastAPI
import threading
import requests
import uvicorn

# Global variables
triggerfaultResolve = False
message_buffer = []  # Buffer to store messages

# FastAPI app initialization
app = FastAPI()

# Function to be called when the send button is pressed
def on_send_button_click():
    global triggerfaultResolve
    triggerfaultResolve = True
    print("trigger", triggerfaultResolve)

async def faultResolve(websocket, fault_type, fault_object, trip_relay, source):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Accurate up to milliseconds
    
    fault_info = {
        "requestType": "ResolveFault",
        "Timestamp": timestamp,
        "FaultType": fault_type,
        "FaultObject": fault_object,
        "TripRelay": trip_relay,
        "Source": source
    }
    
    await websocket.send(json.dumps(fault_info))
    print("\nDEBUG: Sent fault info:", json.dumps(fault_info))

async def unstabilityResolve(websocket, unstable_type, balanceGrid, source):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Accurate up to milliseconds
    
    unstability_info = {
        "requestType": "StabilizeGrid",
        "timestamp": timestamp,
        "balanceGrid": balanceGrid,
        "unstabilityCause": unstable_type,
        "source": source
    }
    
    await websocket.send(json.dumps(unstability_info))
    print("\nDEBUG: Sent unstability info:", json.dumps(unstability_info))

async def data_server(websocket, path):
    global triggerfaultResolve
    global message_buffer

    async for message in websocket:
        try:
            data = json.loads(message)
            request_type = data.get("requestType")
            print(data)
            if request_type == "Value":
                bus_id = data.get("BusID")
                bus_data = data.get("BusData")
                source = data.get("Source")
                timestamp = data.get("timestamp")

                print(f"\nReceived Value Message:\n"
                      f"BusID: {bus_id}\n"
                      f"Source: {source}\n"
                      f"Timestamp: {timestamp}\n"
                      f"Bus Data:\n{bus_data}\n")
                
                # Store the message in the buffer
                message_buffer.append(data)

            else:
                print(f"DEBUG: Unhandled requestType: {request_type}")

            # Check if triggerfaultResolve is True
            if triggerfaultResolve:
                triggerfaultResolve = False  # Reset the trigger
                print("Enter", triggerfaultResolve)
                await faultResolve(websocket, selected_fault_type.get(), "Bus5", True, "S-ZMA")

        except json.JSONDecodeError as e:
            print(f"ERROR: Failed to decode JSON message: {e}")
        except Exception as e:
            print(f"ERROR: An unexpected error occurred: {e}")

# FastAPI route to retrieve buffered data
@app.post("/send_buffered_data")
async def send_buffered_data():
    global message_buffer

    if not message_buffer:
        print("No data to send")
        return {"status": "success", "message": "No data to send"}

    # Send the buffered data to the receiver
    for data in message_buffer:
        try:
            print("Sending data:", data)  # Debugging log
            response = requests.post("http://localhost:8000/receive_data", json=data)
            if response.status_code != 200:
                print(f"Failed to send data. Status code: {response.status_code}")
                return {"status": "error", "message": f"Failed to send data. Status code: {response.status_code}"}
        except Exception as e:
            print(f"Error while sending data: {e}")
            return {"status": "error", "message": str(e)}

    # Clear the buffer after sending
    message_buffer = []
    print("Buffered data sent successfully")
    return {"status": "success", "message": "Buffered data sent successfully"}

# FastAPI route to process received data (This is used to check the data at FastAPI side, if needed)
@app.post("/receive_data")
async def receive_data(data: dict):
    print("Received data in FastAPI:", data)  # Debugging log
    return {"status": "success", "received_data": data}

# Setting up the UI
def setup_ui():
    root = tk.Tk()
    root.title("Fault Trigger UI")

    # Dropdown for fault type
    ttk.Label(root, text="Select Fault Type:").pack(pady=10)
    global selected_fault_type
    selected_fault_type = tk.StringVar()
    fault_type_dropdown = ttk.Combobox(root, textvariable=selected_fault_type)
    fault_type_dropdown['values'] = ("Under-Voltage", "Over-Voltage", "Under-Frequency", "Over-Frequency", "Reactive Power Unstable", "Under-Load", "Over-Load")
    fault_type_dropdown.current(1)  # Default to "Over-Voltage"
    fault_type_dropdown.pack(pady=10)

    # Send button
    send_button = ttk.Button(root, text="Send", command=on_send_button_click)
    send_button.pack(pady=20)

    # Start the Tkinter event loop
    root.mainloop()

async def main():
    # Start WebSocket server
    start_server = websockets.serve(data_server, '0.0.0.0', 8764)
    await start_server
    await asyncio.Future()  # Keeps the server running

if __name__ == "__main__":
    # Run the UI in a separate thread
    ui_thread = threading.Thread(target=setup_ui)
    ui_thread.start()

    # Start the FastAPI server in a separate thread
    api_thread = threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000))
    api_thread.start()

    # Run the WebSocket server in the main thread
    asyncio.run(main())
#######################
import requests
import time

# URL of the FastAPI endpoint to send buffered data
API_URL = "http://localhost:8000/send_buffered_data"

def fetch_buffered_data():
    try:
        # Make a POST request to the FastAPI server to retrieve and send buffered data
        response = requests.post(API_URL)

        # Check if the response status code is 200 (OK)
        if response.status_code == 200:
            result = response.json()  # Parse the JSON response
            print("Server response:", result)
        else:
            print(f"Failed to send buffered data. Status code: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

def main():
    while True:
        fetch_buffered_data()
        time.sleep(1)  # Wait for 1 second before the next fetch

if __name__ == "__main__":
    main()
