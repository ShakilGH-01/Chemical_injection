import serial
import json
import time

# JSON file path
JSON_FILE = 'sensor_data.json'

# Max number of data points to keep
MAX_POINTS = 200

# Initialize data list
data_list = []

# Arduino Serial Setup (adjust the port as needed)
arduino = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

t = 0  # seconds counter

def read_serial_data():
    try:
        line = arduino.readline().decode('utf-8').strip()
        if line:
            # Arduino sends JSON-like {'pH': value} format
            data = json.loads(line.replace("'", "\""))  # safer than eval
            if 'pH' in data:
                return data
    except Exception as e:
        print("Error reading serial:", e)
    return None

def calculate_conductivity(ph):
    # Example: conductivity decreases as pH increases
    conductivity = max(0, 100 - (ph * 5))  # µS/cm
    return round(conductivity, 2)  # round to 2 decimals

try:
    while True:
        sensor_data = read_serial_data()
        if sensor_data:
            ph_value = sensor_data['pH']
            conductivity_value = calculate_conductivity(ph_value)

            # Create JSON data point
            data_point = {
                "time": t,
                "ph": ph_value,
                "conductivity": conductivity_value
            }

            # Append to list
            data_list.append(data_point)

            # Keep only latest MAX_POINTS
            if len(data_list) > MAX_POINTS:
                data_list = data_list[-MAX_POINTS:]

            # Write to JSON file
            with open(JSON_FILE, 'w') as f:
                json.dump(data_list, f, indent=2)

            print(f"Logged data: {data_point}")
            t += 1

        time.sleep(1)

except KeyboardInterrupt:
    print("Stopped")
