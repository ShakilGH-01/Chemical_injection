import json
import time
import random

# JSON file path
JSON_FILE = 'sensor_data.json'

# Mock pH parameters
ph_value = 7.6
style = 0
step = 0.015  # Smooth fast updates
count = 0

def calculate_conductivity(ph):
    # Example: conductivity decreases as pH increases
    conductivity = max(0, 100 - (ph * 5))  # µS/cm
    return round(conductivity, 2)  # 2 decimals

try:
    while True:
        # Change style every 20 readings
        if count % 20 == 0:
            style = random.randint(0, 4)  # 0-4
        count += 1

        # Update pH based on style
        if style == 0:  # linear increase
            ph_value += step
            if ph_value > 8.5:
                ph_value = 7.6
        elif style == 1:  # linear decrease
            ph_value -= step
            if ph_value < 7.6:
                ph_value = 8.5
        elif style == 2:  # random jumps
            ph_value = 7.6 + random.random() * 0.9  # 7.6 -> 8.5
        elif style == 3:  # oscillating
            ph_value += random.choice([-step, step])
            ph_value = max(7.6, min(8.5, ph_value))
        elif style == 4:  # slow drift + noise
            ph_value += random.uniform(-0.005, 0.005)
            ph_value = max(7.6, min(8.5, ph_value))

        # Calculate conductivity
        conductivity_value = calculate_conductivity(ph_value)

        # Create JSON data point (only latest value)
        data_point = {
            "time": count,
            "ph": round(ph_value, 3),
            "conductivity": conductivity_value
        }

        # Overwrite JSON file with **only the latest reading**
        with open(JSON_FILE, 'w') as f:
            json.dump(data_point, f, indent=2)

        print(f"Logged data: {data_point}")

        time.sleep(1)  # Adjust interval as needed

except KeyboardInterrupt:
    # Stop immediately on keyboard input
    print("Keyboard interrupt detected. Stopping.")
