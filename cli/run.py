import serial
import time
from tabulate import tabulate
import re
import os

# --- Serial Port Settings ---
SERIAL_PORT = 'COM13'
BAUD_RATE = 115200
SERIAL_TIMEOUT = 1 

# Regex pattern to identify a valid Wi-Fi data line.
DATA_PATTERN = re.compile(r'^\"[\w\s\-\_]+\",-\d+,\d+,[\d\.]+GHz,[0-9A-Fa-f:]{17},[\w\+\-\_]+$')


def clear_screen():
    """Clears the console screen (works for Windows and Unix/Linux/macOS)."""
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For Unix/Linux/macOS
    else:
        os.system('clear')


def parse_wifi_data(line):
    """Parses a single line of Wi-Fi scan data."""
    
    try:
        start_quote = line.find('"')
        end_quote = line.find('"', start_quote + 1)
        
        if start_quote == -1 or end_quote == -1:
            return None 

        ssid = line[start_quote + 1:end_quote]
        
        remaining_data = line[end_quote + 2:].split(',')
        
        if len(remaining_data) != 5:
            return None

        # [SSID, RSSI, CH, Band, MAC, Encryption]
        return [
            ssid,
            int(remaining_data[0].strip()),
            int(remaining_data[1].strip()),
            remaining_data[2].strip(),
            remaining_data[3].strip(),
            remaining_data[4].strip()
        ]

    except Exception as e:
        return None


def read_and_display_serial_data():
    """Reads data from the serial port and updates a single table in the CLI."""
    
    headers = ["SSID", "RSSI (dBm)", "Channel", "Band", "MAC Address", "Encryption"]
    # We use a persistent list 'current_wifi_data' to build the scan batch
    current_wifi_data = [] 
    
    # Initialize connection message
    print(f"📡 Attempting to connect to serial port **{SERIAL_PORT}** at **{BAUD_RATE}**...")
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=SERIAL_TIMEOUT)
        
        # Clear screen and print initial connection message
        clear_screen()
        print("✅ Connection successful. Waiting for the first scan data...")
        
        while True:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            
            if line:
                # 1. Identify the header line (start of a new scan)
                if line.startswith("SSID,RSSI,CH,Band,MAC,Encryption"):
                    # Clear the list, as a new scan batch is starting
                    current_wifi_data = [] 
                    
                # 2. Identify a valid data line
                elif DATA_PATTERN.match(line):
                    data = parse_wifi_data(line)
                    if data:
                        current_wifi_data.append(data) 
                        
                # 3. Display the table when a scan batch is complete
                # We check if there are no more waiting bytes to signal the end of a block AND we have data.
                if ser.in_waiting == 0 and current_wifi_data:
                    
                    # Sort the data: by Signal Strength (RSSI) in descending order (strongest first)
                    current_wifi_data.sort(key=lambda x: x[1], reverse=True)
                    
                    # --- The key change: Clear screen before displaying the new table ---
                    clear_screen()
                    print("🆕 **Live Wi-Fi Scan Data**")
                    print("-" * 30)
                    
                    # Display the updated table
                    print(tabulate(current_wifi_data, headers=headers, tablefmt="fancy_grid"))
                    
                # 4. Handle other log/error messages
                elif not DATA_PATTERN.match(line):
                    if line.startswith('E') or line.startswith('I') or line.startswith('W'):
                         # Print logs *after* the table or when no table is present
                         print(f"💡 Log Message: {line}")
                         
            else:
                time.sleep(0.01)

    except serial.SerialException as e:
        clear_screen()
        print(f"❌ Serial Port Error on {SERIAL_PORT}: {e}")
        print("Ensure the correct port (COM13) is available and the device is connected.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            print("\nClosing serial connection.")
            ser.close()

if __name__ == "__main__":
    read_and_display_serial_data()