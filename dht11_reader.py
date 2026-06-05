from pigpio_dht import DHT11
import time
import sqlite3
import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
DB_FILE = "sensor_data.db"
gpio_pin = 17
sensor = DHT11(gpio_pin)
BLYNK_TOKEN = os.getenv("BLYNK_AUTH_TOKEN")
BLYNK_BASE = "https://blynk.cloud/external/api"

# Configure logging for network errors
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def init_database():
    """Initialize database schema"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def save_reading(temperature, humidity):
    """Save sensor reading to local database"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO readings (timestamp, temperature, humidity) VALUES (?, ?, ?)",
        (timestamp, temperature, humidity)
    )
    conn.commit()
    conn.close()

def send_to_blynk(temp, humidity):
    """Send data securely to Blynk cloud"""
    if not BLYNK_TOKEN:
        raise RuntimeError("BLYNK_AUTH_TOKEN not set in .env")
        
    # Send temperature to V0
    r1 = requests.get(
        f"{BLYNK_BASE}/update",
        params={"token": BLYNK_TOKEN, "V0": temp},
        timeout=5
    )
    r1.raise_for_status()
    
    # Send humidity to V1
    r2 = requests.get(
        f"{BLYNK_BASE}/update",
        params={"token": BLYNK_TOKEN, "V1": humidity},
        timeout=5
    )
    r2.raise_for_status()

if __name__ == "__main__":
    init_database()
    print(f"Starting Hardware-DMA sensor read on GPIO {gpio_pin}. Press Ctrl+C to quit.")

    while True:
        try:
            result = sensor.read()
            
            if result.get('valid'):
                temp = result.get('temp_c')
                hum = result.get('humidity')
                
                # 1. Save locally first (Always!)
                save_reading(temp, hum)
                
                # 2. Attempt to push to cloud with error handling [cite: 990-1000]
                try:
                    send_to_blynk(temp, hum)
                    logging.info(f"Success! Temp: {temp}°C, Hum: {hum}% | Data saved locally & sent to Blynk!")
                except requests.exceptions.Timeout:
                    logging.error("Blynk timeout - Data saved locally only.")
                except requests.exceptions.ConnectionError:
                    logging.error("Network unavailable - Data saved locally only.")
                except Exception as e:
                    logging.error(f"Unexpected cloud error: {e}")
                
            else:
                logging.warning("Checksum failed or missed signal. Retrying...")
                
        except TimeoutError:
            logging.error("Sensor not responding. Check wiring to GPIO 17.")
        except Exception as e:
            logging.error(f"Hardware Error: {e}")
            
        time.sleep(2)
