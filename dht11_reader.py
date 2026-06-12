from pigpio_dht import DHT11
import time
import sqlite3
import os
import requests
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load secrets from .env file
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
            humidity REAL NOT NULL,
            synced INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def save_reading(temperature, humidity):
    """Save sensor reading and return its ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    
    # Notice we insert 0 for synced initially
    cursor.execute(
        "INSERT INTO readings (timestamp, temperature, humidity, synced) VALUES (?, ?, ?, 0)",
        (timestamp, temperature, humidity)
    )
    reading_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reading_id

def mark_as_synced(reading_id):
    """Update database to show data reached the cloud"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE readings SET synced=1 WHERE id=?", (reading_id,))
    conn.commit()
    conn.close()

def send_to_blynk(temp, humidity):
    """Core Blynk push"""
    if not BLYNK_TOKEN:
        raise RuntimeError("BLYNK_AUTH_TOKEN not set in .env")
        
    r1 = requests.get(f"{BLYNK_BASE}/update", params={"token": BLYNK_TOKEN, "V0": temp}, timeout=5)
    r1.raise_for_status()
    
    r2 = requests.get(f"{BLYNK_BASE}/update", params={"token": BLYNK_TOKEN, "V1": humidity}, timeout=5)
    r2.raise_for_status()

def send_to_blynk_safe(temp, humidity, reading_id):
    """Wraps the push in a try/except to catch failures"""
    try:
        send_to_blynk(temp, humidity)
        mark_as_synced(reading_id)
        logging.info(f"Success! Data sent and synced (ID: {reading_id})")
        return True
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        logging.error("Network unavailable - Data buffered locally.")
        return False
    except Exception as e:
        logging.error(f"Cloud send failed: {e}. Data buffered locally.")
        return False

def resend_unsynced():
    """Look for stranded data and resend it"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, temperature, humidity FROM readings WHERE synced=0")
    rows = cursor.fetchall()
    
    if rows:
        logging.info(f"Attempting to resend {len(rows)} buffered readings...")
        
    for row in rows:
        reading_id, temp, hum = row
        time.sleep(0.5) # Prevent rate-limiting when sending a backlog
        send_to_blynk_safe(temp, hum, reading_id)
        
    conn.close()

if __name__ == "__main__":
    init_database()
    print(f"Starting Hardware-DMA sensor read on GPIO {gpio_pin}. Press Ctrl+C to quit.")

    while True:
        try:
            result = sensor.read()
            
            if result.get('valid'):
                temp = result.get('temp_c')
                hum = result.get('humidity')
                
                # 1. Save locally and get the row ID
                reading_id = save_reading(temp, hum)
                
                # 2. Try to send the current reading
                send_to_blynk_safe(temp, hum, reading_id)
                
                # 3. Check for and send any past data that failed
                resend_unsynced()
                
            else:
                logging.warning("Checksum failed or missed signal. Retrying...")
                
        except TimeoutError:
            logging.error("Sensor not responding. Check wiring.")
        except Exception as e:
            logging.error(f"Hardware Error: {e}")
            
        time.sleep(2)
